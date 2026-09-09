# Copyright (c) 2026 Mark Hawksworth (https://github.com/hawkers63/). All Rights Reserved.
#
# Desktop Vista is proprietary software. Unauthorised copying, reproduction,
# redistribution, modification, reverse-engineering, or commercial use of this
# file or any portion of it is strictly prohibited without prior written consent
# from the copyright holder (Mark Hawksworth — https://github.com/hawkers63/).
#
# See the LICENSE file in the project root for the full proprietary notice.
"""
Desktop Vista — global hotkeys (v1.6), ctypes-only (no pywin32).

RegisterHotKey/WM_HOTKEY is thread-affine: registering with hWnd=None posts
WM_HOTKEY to the *registering thread's* message queue, not to any window's
WndProc. Rather than subclassing Tk's own top-level window (fragile — the
subclass callback's lifetime has to outlive every inbound message, and it
competes with Tcl/Tk's own internal message pump on that HWND), this runs
its own dedicated thread that registers every binding and then pumps
GetMessage itself. Firing a hotkey never touches Tk directly: the fired id
goes to the caller's *on_hotkey* callback, which desktop_vista.py wraps in
`root.after(0, ...)` to marshal back onto the Tk thread — the same pattern
already used for ipc.IpcServer.

A second background GetMessage loop alongside pystray's own tray-icon
message loop is safe: each thread that owns a message queue (any thread
that calls RegisterHotKey/GetMessage) gets an independent queue from
Windows, so the two never contend for the same messages.
"""

from __future__ import annotations

import sys
import threading
from typing import Callable, Optional

try:
    import ctypes
    from ctypes import wintypes
except ImportError:  # pragma: no cover - non-Windows
    ctypes = None  # type: ignore[assignment]
    wintypes = None  # type: ignore[assignment]

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000  # suppress a repeat WM_HOTKEY storm while the key is held

_MODIFIER_FLAGS = {
    "win": MOD_WIN,
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
}


def is_available() -> bool:
    return ctypes is not None and sys.platform == "win32"


def _vk_for_key(key: str) -> Optional[int]:
    """Virtual-key code for a single trailing key token. A-Z and 0-9 map
    directly to their ASCII value on Windows; anything else (function
    keys, punctuation) isn't needed by the default bindings and is
    deliberately not supported yet, to keep parsing unambiguous."""
    key = key.strip().upper()
    if len(key) == 1 and ("A" <= key <= "Z" or "0" <= key <= "9"):
        return ord(key)
    return None


def parse_binding(text: str) -> Optional[tuple[int, int]]:
    """Parse "Win+Alt+N" into (modifiers, vk). None if malformed, or if it
    has no modifier at all — a bare key would steal normal typing anywhere
    else in the app or the OS."""
    parts = [p for p in (s.strip() for s in text.split("+")) if p]
    if len(parts) < 2:
        return None
    *mod_parts, key_part = parts
    mods = 0
    for part in mod_parts:
        flag = _MODIFIER_FLAGS.get(part.lower())
        if flag is None:
            return None
        mods |= flag
    vk = _vk_for_key(key_part)
    if vk is None:
        return None
    return mods | MOD_NOREPEAT, vk


def format_binding(mods: int, vk: int) -> str:
    """Inverse of parse_binding's modifier side, for status/log display."""
    names = []
    if mods & MOD_WIN:
        names.append("Win")
    if mods & MOD_CONTROL:
        names.append("Ctrl")
    if mods & MOD_ALT:
        names.append("Alt")
    if mods & MOD_SHIFT:
        names.append("Shift")
    names.append(chr(vk) if 0 <= vk < 256 else f"0x{vk:02X}")
    return "+".join(names)


class HotkeyListener(threading.Thread):
    """Owns a RegisterHotKey message queue on its own thread.

    *bindings*: [(id, modifiers, vk), ...]. *on_hotkey* is called with the
    fired id from this thread — the caller must marshal it (e.g. Tk's
    `root.after(0, ...)`) before touching any UI state.

    After start(), wait on `.ready` (set once every binding attempt has
    been made) then read `.conflicts` — ids that failed to register,
    almost always because another application already owns that
    combination. A conflict is reported, never silently retried.
    """

    def __init__(self, bindings: list[tuple[int, int, int]], on_hotkey: Callable[[int], None]):
        super().__init__(name="dv-hotkeys", daemon=True)
        self._bindings = bindings
        self._on_hotkey = on_hotkey
        self._thread_id: Optional[int] = None
        self.ready = threading.Event()
        self.conflicts: list[str] = []

    def run(self) -> None:  # pragma: no cover - Windows-only, exercised via live smoke test
        if not is_available():
            self.ready.set()
            return
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()
        registered: list[int] = []
        for hotkey_id, mods, vk in self._bindings:
            if user32.RegisterHotKey(None, hotkey_id, mods, vk):
                registered.append(hotkey_id)
            else:
                self.conflicts.append(format_binding(mods & ~MOD_NOREPEAT, vk))
        self.ready.set()
        try:
            msg = wintypes.MSG()
            while True:
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret <= 0:  # WM_QUIT (0) or an error (-1)
                    break
                if msg.message == WM_HOTKEY:
                    try:
                        self._on_hotkey(int(msg.wParam))
                    except Exception:
                        pass  # a bad handler must never kill the listener thread
        finally:
            for hotkey_id in registered:
                user32.UnregisterHotKey(None, hotkey_id)

    def stop(self) -> None:
        """Ask the loop to exit via PostThreadMessage(WM_QUIT) — GetMessage
        wakes immediately, unlike a poll. Safe to call even if the thread
        never fully started (checks the id it recorded, not is_alive)."""
        if self._thread_id is not None and is_available():
            try:
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
