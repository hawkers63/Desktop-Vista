# Copyright (c) 2026 Mark Hawksworth (https://github.com/hawkers63/). All Rights Reserved.
#
# Desktop Vista is proprietary software. Unauthorised copying, reproduction,
# redistribution, modification, reverse-engineering, or commercial use of this
# file or any portion of it is strictly prohibited without prior written consent
# from the copyright holder (Mark Hawksworth — https://github.com/hawkers63/).
#
# See the LICENSE file in the project root for the full proprietary notice.
"""
Desktop Vista — single-instance guard and CLI IPC bridge (v1.6).

Two pieces, both ctypes-only (no pywin32, matching the rest of the app):

  - Single-instance mutex (`try_become_primary`) so a second launch — e.g.
    two Windows-logon Run-key races, or a user double-clicking the exe
    while it's already running in the tray — doesn't run two slideshow
    engines applying wallpapers concurrently.

  - A named-pipe request/response server (`IpcServer`) so a second launch,
    or an external script/Task Scheduler/Stream Deck, can control the
    already-running instance (`--next`, `--status`, ...) instead of a
    second window opening. One client at a time, newline-delimited JSON,
    request then reply then close. The pipe is created with an owner-only
    security descriptor (SDDL "D:P(A;;GA;;;OW)") so another local user's
    process cannot drive this instance's wallpaper — SECURITY_WORLD/a NULL
    DACL is deliberately not used here.

The server thread never touches Tk state directly: each parsed request is
handed to a *dispatch* callback through a *marshal* function the caller
supplies (desktop_vista.py passes `root.after(0, ...)`), and the pipe
thread blocks — with a timeout — for dispatch to finish and hand back a
reply dict.
"""

from __future__ import annotations

import json
import sys
import threading
from typing import Any, Callable, Optional

try:
    import ctypes
    from ctypes import wintypes
except ImportError:  # pragma: no cover - non-Windows
    ctypes = None  # type: ignore[assignment]
    wintypes = None  # type: ignore[assignment]

APP_ID = "DesktopVista"
MUTEX_NAME = f"Local\\{APP_ID}.SingleInstance"
PIPE_NAME = rf"\\.\pipe\{APP_ID}.Ipc"

ERROR_ALREADY_EXISTS = 183
ERROR_PIPE_CONNECTED = 535
ERROR_PIPE_BUSY = 231

PIPE_ACCESS_DUPLEX = 0x00000003
PIPE_TYPE_MESSAGE = 0x00000004
PIPE_READMODE_MESSAGE = 0x00000002
PIPE_WAIT = 0x00000000
PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
PIPE_UNLIMITED_INSTANCES = 255
BUFFER_SIZE = 65536

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3

DISPATCH_TIMEOUT_S = 8.0
CLIENT_TIMEOUT_S = 5.0


def is_available() -> bool:
    return ctypes is not None and sys.platform == "win32"


def try_become_primary() -> tuple[Any, bool]:
    """Attempt to become the single primary instance.

    Returns (mutex_handle, is_primary). Keep *mutex_handle* alive for the
    process lifetime and pass it to release_primary() on exit — releasing
    or exiting is what lets a later launch become primary. On non-Windows,
    or if the guard itself can't run, degrades to (None, True): a
    diagnostic/scripting feature must never block the app from starting.
    """
    if not is_available():
        return None, True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    if not handle:
        return None, True
    already_exists = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
    return handle, not already_exists


def release_primary(handle: Any) -> None:
    if handle is None or not is_available():
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    try:
        kernel32.ReleaseMutex(handle)
    except Exception:
        pass
    try:
        kernel32.CloseHandle(handle)
    except Exception:
        pass


class _SecurityAttributes(ctypes.Structure if ctypes is not None else object):
    _fields_ = (
        [
            ("nLength", wintypes.DWORD),
            ("lpSecurityDescriptor", ctypes.c_void_p),
            ("bInheritHandle", wintypes.BOOL),
        ]
        if ctypes is not None
        else []
    )


def _owner_only_security_attributes() -> "_SecurityAttributes":
    """SECURITY_ATTRIBUTES granting full control to the pipe's creator
    only, via SDDL "D:P(A;;GA;;;OW)" (protected DACL; owner: generic-all) —
    so another local user's process cannot open this pipe. The descriptor
    is intentionally never freed; it lives for the server thread's
    lifetime and the OS reclaims it at process exit."""
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    psd = ctypes.c_void_p()
    ok = advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        "D:P(A;;GA;;;OW)", 1, ctypes.byref(psd), None
    )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    sa = _SecurityAttributes()
    sa.nLength = ctypes.sizeof(_SecurityAttributes)
    sa.lpSecurityDescriptor = psd
    sa.bInheritHandle = False
    return sa


class IpcServer(threading.Thread):
    """Named-pipe request/response server. Runs on its own daemon thread;
    never calls into Tk or COM directly (house rule — see notes/notes_005
    §0). Each connection: read one line of JSON, hand it to *dispatch* via
    *marshal*, wait (bounded) for a reply, write one line of JSON, close."""

    def __init__(
        self,
        dispatch: Callable[[dict], dict],
        marshal: Callable[[Callable[[], None]], None],
    ) -> None:
        super().__init__(name="dv-ipc", daemon=True)
        self._dispatch = dispatch
        self._marshal = marshal
        self._stop_event = threading.Event()
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True) if is_available() else None

    def stop(self) -> None:
        self._stop_event.set()
        # ConnectNamedPipe blocks until a client connects; wake it with a
        # throwaway connection so the loop notices _stop_event promptly
        # instead of waiting for the next real client.
        if self._kernel32 is not None:
            try:
                send_command({"cmd": "ping"}, timeout=0.5)
            except OSError:
                pass

    def run(self) -> None:  # pragma: no cover - Windows-only, exercised via live smoke test
        if self._kernel32 is None:
            return
        k32 = self._kernel32
        try:
            sa = _owner_only_security_attributes()
        except OSError:
            return
        while not self._stop_event.is_set():
            handle = k32.CreateNamedPipeW(
                PIPE_NAME,
                PIPE_ACCESS_DUPLEX,
                PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
                PIPE_UNLIMITED_INSTANCES,
                BUFFER_SIZE,
                BUFFER_SIZE,
                0,
                ctypes.byref(sa),
            )
            if handle in (0, -1):
                return
            connected = k32.ConnectNamedPipe(handle, None)
            if not self._stop_event.is_set() and (
                connected or ctypes.get_last_error() == ERROR_PIPE_CONNECTED
            ):
                self._serve(handle)
            k32.CloseHandle(handle)

    def _serve(self, handle: Any) -> None:
        k32 = self._kernel32
        buf = ctypes.create_string_buffer(BUFFER_SIZE)
        read = wintypes.DWORD()
        if not k32.ReadFile(handle, buf, BUFFER_SIZE, ctypes.byref(read), None):
            return
        raw = buf.raw[: read.value].decode("utf-8", "replace").strip()
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("payload is not a JSON object")
        except (json.JSONDecodeError, ValueError):
            reply: dict = {"ok": False, "error": "invalid request"}
        else:
            reply = self._dispatch_blocking(payload)
        data = (json.dumps(reply) + "\n").encode("utf-8")
        written = wintypes.DWORD()
        k32.WriteFile(handle, data, len(data), ctypes.byref(written), None)
        k32.FlushFileBuffers(handle)
        k32.DisconnectNamedPipe(handle)

    def _dispatch_blocking(self, payload: dict) -> dict:
        done = threading.Event()
        box: dict = {}

        def _run_on_owner_thread() -> None:
            try:
                box["reply"] = self._dispatch(payload)
            except Exception as exc:  # a bad command must never crash the UI thread
                box["reply"] = {"ok": False, "error": str(exc)}
            finally:
                done.set()

        self._marshal(_run_on_owner_thread)
        if not done.wait(timeout=DISPATCH_TIMEOUT_S):
            return {"ok": False, "error": "timed out waiting for the running instance"}
        return box.get("reply", {"ok": False, "error": "no reply"})


def send_command(payload: dict, timeout: float = CLIENT_TIMEOUT_S) -> dict:
    """Connect to an already-running instance's pipe, send one JSON
    request, return its JSON reply. Raises OSError if nothing is
    listening (no primary instance) or on any I/O failure."""
    if not is_available():
        raise OSError("IPC is only available on Windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.CreateFileW(
        PIPE_NAME, GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None
    )
    if handle in (0, -1):
        if ctypes.get_last_error() == ERROR_PIPE_BUSY:
            kernel32.WaitNamedPipeW(PIPE_NAME, int(timeout * 1000))
            handle = kernel32.CreateFileW(
                PIPE_NAME, GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None
            )
        if handle in (0, -1):
            raise ctypes.WinError(ctypes.get_last_error())
    try:
        mode = wintypes.DWORD(PIPE_READMODE_MESSAGE)
        kernel32.SetNamedPipeHandleState(handle, ctypes.byref(mode), None, None)
        data = (json.dumps(payload) + "\n").encode("utf-8")
        written = wintypes.DWORD()
        if not kernel32.WriteFile(handle, data, len(data), ctypes.byref(written), None):
            raise ctypes.WinError(ctypes.get_last_error())
        buf = ctypes.create_string_buffer(BUFFER_SIZE)
        read = wintypes.DWORD()
        if not kernel32.ReadFile(handle, buf, BUFFER_SIZE, ctypes.byref(read), None):
            raise ctypes.WinError(ctypes.get_last_error())
        raw = buf.raw[: read.value].decode("utf-8", "replace").strip()
        return json.loads(raw)
    finally:
        kernel32.CloseHandle(handle)


def cli_payload(argv: list[str]) -> Optional[dict]:
    """Map recognised CLI flags to an IPC command payload for controlling
    an already-running instance. None if no such flag is present."""
    if "--set" in argv:
        idx = argv.index("--set")
        if idx + 1 < len(argv) and argv[idx + 1]:
            return {"cmd": "set", "path": argv[idx + 1]}
        return None
    flag_to_cmd = {
        "--next": "next",
        "--prev": "prev",
        "--pause": "pause",
        "--resume": "resume",
        "--toggle": "toggle",
        "--status": "status",
        "--favourite": "favourite",
        "--hide": "hide",
        "--undo": "undo",
    }
    for flag, cmd in flag_to_cmd.items():
        if flag in argv:
            return {"cmd": cmd}
    return None
