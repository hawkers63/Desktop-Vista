# Copyright (c) 2026 Mark Hawksworth (https://github.com/hawkers63/). All Rights Reserved.
#
# Desktop Vista is proprietary software. Unauthorised copying, reproduction,
# redistribution, modification, reverse-engineering, or commercial use of this
# file or any portion of it is strictly prohibited without prior written consent
# from the copyright holder (Mark Hawksworth — https://github.com/hawkers63/).
#
# See the LICENSE file in the project root for the full proprietary notice.
"""
windows_wallpaper_com.py — Experimental IDesktopWallpaper COM backend (v2.0).

Desktop Vista's default wallpaper path is the global SystemParametersInfoW
call in desktop_vista.py (config.wallpaper_target == "spi", the default).
This module is an OPT-IN alternative (wallpaper_target == "com") that can
target one specific monitor via IDesktopWallpaper, available on Windows 8+.

Import this module lazily and expect it to be missing: it requires
`comtypes` (not a core dependency — see requirements.txt) and only makes
sense on Windows. desktop_vista.py wraps the import in try/except and
disables the experimental toggle entirely when it's unavailable.

Verification status (read before trusting this beyond "it imports"):
verified on the development machine that COM object construction, monitor
enumeration, and SetWallpaper/SetPosition targeting the global (monitor_id
= None) target all succeed and visibly change the desktop. That machine
has exactly one display attached — true per-monitor independence (two
different images on two different displays, not touching each other) has
NOT been visually confirmed anywhere in this codebase's history. Treat
that specific claim as unverified until checked on real multi-monitor
hardware.

Known limitations carried over from notes/notes_004.txt's review, not
resolved here:
    - COM calls across displays are not an atomic transaction; a partial
      failure (one display succeeds, another fails) is reported as an
      exception from whichever call failed, with no automatic rollback of
      the display(s) that already changed.
    - SetPosition (fit style) is a global desktop setting, not per-monitor
      — Windows has no per-monitor fit style. Span requires the
      all-displays target and is rejected here for a specific monitor.
    - GetMonitorDevicePathAt's returned identity has no persistence
      handling here (docking/driver changes can reassign device paths);
      callers should treat monitor_id strings as ephemeral within a
      session, not stored as a stable long-term key without reconciliation.
"""

from __future__ import annotations

import ctypes
import queue
import sys
import threading
from ctypes import POINTER, c_int, c_uint, c_void_p, c_wchar_p
from ctypes.wintypes import RECT
from typing import Any, Callable, Optional

if sys.platform != "win32":
    raise ImportError("windows_wallpaper_com is Windows-only.")

import comtypes  # noqa: E402 - platform-gated import, see above
from comtypes import COMMETHOD, GUID, HRESULT, IUnknown  # noqa: E402
from comtypes.client import CreateObject  # noqa: E402

_CLSID_DESKTOP_WALLPAPER = GUID("{C2CF3110-460E-4FC1-B9D0-8A1C0C9CC4BD}")
_IID_IDESKTOP_WALLPAPER = GUID("{B92B56A9-8B55-4E14-9A89-0199BBB6F93B}")

# DESKTOP_WALLPAPER_POSITION enum (shobjidl_core.h). SetPosition is a global
# desktop setting; there is no per-monitor fit style in this API.
POSITION_VALUES: dict[str, int] = {
    "Centre": 0, "Tile": 1, "Stretch": 2, "Fit": 3, "Fill": 4, "Span": 5,
}

_DEFAULT_CALL_TIMEOUT = 5.0


class ComWallpaperError(RuntimeError):
    """Raised for any COM/HRESULT failure or timeout from this backend."""


class IDesktopWallpaper(IUnknown):
    """
    Declares the vtable prefix through SetPosition, in native declaration
    order (shobjidl_core.h) — comtypes builds the vtable proxy strictly
    from this list's order, so it must not skip or reorder any method
    actually present ahead of the ones declared. Slideshow-related methods
    that follow SetPosition in the real interface are intentionally left
    undeclared since nothing here calls them; that's a valid partial
    binding as long as no one calls past what's declared.
    """

    _iid_ = _IID_IDESKTOP_WALLPAPER
    _methods_ = [
        COMMETHOD([], HRESULT, "SetWallpaper",
                  (["in"], c_wchar_p, "monitorID"),
                  (["in"], c_wchar_p, "wallpaper")),
        COMMETHOD([], HRESULT, "GetWallpaper",
                  (["in"], c_wchar_p, "monitorID"),
                  (["out"], POINTER(c_void_p), "wallpaper")),
        COMMETHOD([], HRESULT, "GetMonitorDevicePathAt",
                  (["in"], c_uint, "monitorIndex"),
                  (["out"], POINTER(c_void_p), "monitorID")),
        COMMETHOD([], HRESULT, "GetMonitorDevicePathCount",
                  (["out"], POINTER(c_uint), "count")),
        COMMETHOD([], HRESULT, "GetMonitorRECT",
                  (["in"], c_wchar_p, "monitorID"),
                  (["out"], POINTER(RECT), "displayRect")),
        COMMETHOD([], HRESULT, "SetBackgroundColor",
                  (["in"], c_uint, "color")),
        COMMETHOD([], HRESULT, "GetBackgroundColor",
                  (["out"], POINTER(c_uint), "color")),
        COMMETHOD([], HRESULT, "SetPosition",
                  (["in"], c_int, "position")),
    ]


def _free_com_string(address: int) -> None:
    free = ctypes.OleDLL("ole32").CoTaskMemFree
    free.argtypes = [c_void_p]
    free.restype = None
    free(address)


def _enumerate_monitors(wallpaper: "IDesktopWallpaper") -> list[tuple[str, tuple[int, int, int, int]]]:
    """Runs on the owning STA thread — see ComWallpaperBackend."""
    monitors: list[tuple[str, tuple[int, int, int, int]]] = []
    count = wallpaper.GetMonitorDevicePathCount()
    for index in range(count):
        address = wallpaper.GetMonitorDevicePathAt(index)
        try:
            device_id = ctypes.wstring_at(address)
        finally:
            _free_com_string(address)
        rect = wallpaper.GetMonitorRECT(device_id)
        monitors.append((device_id, (rect.left, rect.top, rect.right, rect.bottom)))
    return monitors


class ComWallpaperBackend:
    """
    Owns one dedicated STA thread; every public method dispatches onto it
    and blocks for the result. comtypes pointers created under
    CoInitializeEx(APARTMENTTHREADED) must only be used from that same
    thread — do not share an instance's internal COM pointer across
    threads, and do not call these methods from a decode worker thread;
    call them from the UI thread and expect a short block.
    """

    def __init__(self) -> None:
        self._requests: "queue.Queue[Optional[tuple[Callable, tuple, queue.Queue]]]" = queue.Queue()
        self._closed = False
        self._thread = threading.Thread(
            target=self._run, name="dv-com-wallpaper", daemon=True
        )
        self._thread.start()

    def _run(self) -> None:
        comtypes.CoInitializeEx(comtypes.COINIT_APARTMENTTHREADED)
        try:
            while True:
                item = self._requests.get()
                if item is None:
                    return
                func, args, result_q = item
                try:
                    result_q.put(("ok", func(*args)))
                except Exception as exc:  # surfaced to the caller, never swallowed
                    result_q.put(("error", exc))
        finally:
            comtypes.CoUninitialize()

    def _call(self, func: Callable, *args, timeout: float = _DEFAULT_CALL_TIMEOUT) -> Any:
        if self._closed:
            raise ComWallpaperError("COM wallpaper backend is closed.")
        result_q: "queue.Queue[tuple[str, Any]]" = queue.Queue(maxsize=1)
        self._requests.put((func, args, result_q))
        try:
            status, value = result_q.get(timeout=timeout)
        except queue.Empty:
            raise ComWallpaperError("COM wallpaper call timed out.") from None
        if status == "error":
            raise ComWallpaperError(str(value)) from value
        return value

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._requests.put(None)

    # ---- Operations dispatched onto the STA thread ----

    @staticmethod
    def _enumerate_monitors_sta() -> list[tuple[str, tuple[int, int, int, int]]]:
        wallpaper = CreateObject(
            _CLSID_DESKTOP_WALLPAPER, interface=IDesktopWallpaper, clsctx=comtypes.CLSCTX_ALL
        )
        return _enumerate_monitors(wallpaper)

    def enumerate_monitors(self) -> list[tuple[str, tuple[int, int, int, int]]]:
        """Return [(device_path, (left, top, right, bottom)), ...]."""
        return self._call(self._enumerate_monitors_sta)

    @staticmethod
    def _set_wallpaper_sta(monitor_id: Optional[str], path: str, style: str) -> None:
        if style == "Span" and monitor_id is not None:
            # Checked before touching COM at all: this is a request-shape
            # error, not something the API itself needs to reject.
            raise ComWallpaperError("Span requires the all-displays target.")
        wallpaper = CreateObject(
            _CLSID_DESKTOP_WALLPAPER, interface=IDesktopWallpaper, clsctx=comtypes.CLSCTX_ALL
        )
        if monitor_id is not None:
            known_ids = {device_id for device_id, _rect in _enumerate_monitors(wallpaper)}
            if monitor_id not in known_ids:
                raise ComWallpaperError(f"Monitor {monitor_id!r} is no longer connected.")
        position = POSITION_VALUES.get(style, POSITION_VALUES["Fill"])
        wallpaper.SetPosition(position)  # global fit policy — comtypes raises COMError on failure
        wallpaper.SetWallpaper(monitor_id, str(path))

    def set_wallpaper(self, monitor_id: Optional[str], path: str, style: str) -> None:
        """
        Apply *path* to *monitor_id* (a device path from enumerate_monitors),
        or to every display if *monitor_id* is None. Raises ComWallpaperError
        on any failure — callers get an explicit error, never a silent
        partial success.
        """
        self._call(self._set_wallpaper_sta, monitor_id, path, style)
