# Copyright (c) 2026 Mark Hawksworth (https://github.com/hawkers63/). All Rights Reserved.
#
# Desktop Vista is proprietary software. Unauthorised copying, reproduction,
# redistribution, modification, reverse-engineering, or commercial use of this
# file or any portion of it is strictly prohibited without prior written consent
# from the copyright holder (Mark Hawksworth — https://github.com/hawkers63/).
#
# See the LICENSE file in the project root for the full proprietary notice.
"""
Desktop Vista  —  All my drives. One perfect view.
Version 1.5.0  (September 2026)

A lightweight Windows wallpaper manager.

Location : D:\\Desktop_Vista\\desktop_vista.py
Config   : D:\\Desktop_Vista\\config.json  (created automatically)

Requirements (run once):
    pip install customtkinter pillow pystray

Features in v1.1 (hardened):
    - Manage any number of wallpaper folders across any drives
    - Fast 16:9 preview (decoded straight to preview size, not full 4K)
    - Previous / Next / Random navigation with Fisher–Yates shuffle deck
    - Set as Wallpaper with Fill / Fit / Stretch / Centre / Span style
    - Folder slideshow with interval and shuffle; timer resets on manual nav
    - Debounced config saves; atomic write; typed load with defaults
    - Background thumbnail loading with generation tokens
    - WebP/non-native formats transcoded to JPEG cache for wallpaper apply
    - EXIF orientation correction; dynamic preview resize; richer shortcuts
    - Remembers folders, style, interval, shuffle and last image

New in v1.2 "Silent Companion":
    - System tray icon (pystray) with the branded Desktop Vista glyph;
      close hides to tray instead of quitting
    - Tray menu: current image, Next/Previous (now applies the wallpaper,
      not just the preview), Pause/Resume slideshow, Reveal in Explorer,
      Open Desktop Vista, Exit
    - --minimized launch flag + "Start with Windows" Run-key toggle
    - Custom slideshow interval in seconds ("Custom…" + a prompt)
    - Offline-aware folders: "(offline)" badge in the folder dropdown,
      unattended slideshow skips missing files instead of popping a
      blocking error dialog

v1.2.1 hardening addendum (see notes/notes_004.txt review):
    - Branded window/tray icon loaded from icon/desktop_vista.ico
    - Fixed a stale-exception NameError risk in the preview error callback
    - Tray Next/Previous now actually re-apply the wallpaper
    - Tray startup readiness is tracked explicitly; --minimized falls back
      to a visible window if the tray failed to come up
    - Folder switches invalidate any in-flight preview load, even when the
      new folder is empty
    - Config defaults are deep-copied (a shared mutable default could leak
      between validation passes); tray flags require real booleans;
      non-finite custom intervals are rejected instead of crashing
    - Config saves use a unique temp file per write, avoiding a rename
      race between two running instances
    - Preview decoding reads EXIF orientation before requesting a Pillow
      draft box, so rotated images still get the fast reduced decode
    - Shuffle deck advances via a cursor instead of list.pop(0)
    - "Start with Windows" reflects whether the registry command still
      matches this install, not just whether some value exists

New in v1.3 "All My Drives":
    - Playlists: named groups of folders played as one aggregated,
      deduplicated source, spanning any number of drives
    - Favourites (♡) and Hide (🙈) — non-destructive; hidden images are
      filtered out of playback everywhere without touching the source file
    - Drive reconnect watcher: offline badges and empty sources refresh on
      a 15s poll without needing a manual reselect
    - Playback source generalised to folder-or-playlist (`playback_source`
      in config); `current_folder` kept in sync for older readers

New in v1.4 "Power & Context Awareness":
    - Auto-pause on Battery Saver (GetSystemPowerStatus) and while a
      fullscreen app/game or presentation is active
      (SHQueryUserNotificationState) — independent pause reasons, so
      resuming from one can't accidentally resume while the other still
      applies; manual Start/Stop intent is tracked separately from the
      currently-scheduled tick, so a resume picks back up automatically
    - Daily-times schedule mode as an alternative to a fixed interval
      ("run at these times of day"); recomputes the next trigger fresh on
      every tick rather than caching one, so it self-corrects across a
      DST change or clock adjustment
    - Mica/Acrylic backdrop experiment dropped from scope — disproportionate
      implementation risk for a CustomTkinter app relative to its value

New in v1.5 "Foundations for v2.0":
    - Read-only monitor topology strip (Win32 EnumDisplayMonitors /
      GetMonitorInfoW — no COM needed for read-only enumeration); shows
      the real arrangement, does not change what's applied anywhere
    - Tags (freeform, per image) and collections (saved "match any of
      these tags" filters) — a third playback-source kind alongside
      folders and playlists, spanning every tagged image across drives
    - Solar dawn/day/dusk/night data model (coordinates + 4 fallback
      times) — validated and stored, not yet wired into the live
      schedule; that wiring, like per-monitor apply, is v2.0's job

Planned for v2.0: multi-monitor (IDesktopWallpaper COM), built behind an
opt-in experimental flag — see ROADMAP.md for what's been verified versus
what still needs multi-monitor hardware to confirm.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

# Optional Windows-only modules — must not break import on Linux (tests).
try:
    import ctypes
except ImportError:  # pragma: no cover
    ctypes = None  # type: ignore[assignment]

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore[assignment]

try:
    import pystray
except ImportError:
    pystray = None  # type: ignore[assignment]

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps
from tkinter import Canvas, filedialog, messagebox, simpledialog

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("desktop_vista")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

APP_NAME = "Desktop Vista"
APP_VERSION = "1.5.0"
TAGLINE = "All my drives. One perfect view."

# Frozen (PyInstaller) builds extract bundled files under a temporary
# sys._MEIPASS directory each run; __file__ there does NOT sit beside the
# .exe. Config must live next to the real executable so it survives past a
# single run, while bundled read-only assets (the icon) are read from the
# extraction dir.
FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    APP_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = APP_DIR

CONFIG_PATH = APP_DIR / "config.json"
BRAND_ICON_PATH = RESOURCE_DIR / "icon" / "desktop_vista.ico"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
NATIVE_WALLPAPER_EXTS = {".jpg", ".jpeg", ".bmp", ".png"}

# Windows registry values for the wallpaper "fit" style.
# (WallpaperStyle, TileWallpaper)
WALLPAPER_STYLES = {
    "Fill": ("10", "0"),
    "Fit": ("6", "0"),
    "Stretch": ("2", "0"),
    "Centre": ("0", "0"),
    "Span": ("22", "0"),
}

SLIDESHOW_INTERVALS = {
    "1 minute": 60,
    "5 minutes": 300,
    "15 minutes": 900,
    "30 minutes": 1800,
    "1 hour": 3600,
    "6 hours": 21600,
    "1 day": 86400,
}
CUSTOM_INTERVAL_LABEL = "Custom…"
MIN_CUSTOM_INTERVAL_SECONDS = 5
MAX_CUSTOM_INTERVAL_SECONDS = 86400

OFFLINE_SUFFIX = "  (offline)"

PREVIEW_W, PREVIEW_H = 800, 450  # 16:9 default; recalculated dynamically
SAVE_DEBOUNCE_MS = 600
ASPECT_RATIO = 16 / 9

DEFAULT_CONFIG: dict[str, Any] = {
    "folders": [],
    "current_folder": None,
    "current_image": None,
    "style": "Fill",
    "interval": "15 minutes",
    "shuffle": False,
    "interval_custom_seconds": None,
    "tray": {"enabled": True, "close_to_tray": True, "run_at_startup": False},
    # v1.3 "All My Drives" — additive; a config with none of these still
    # loads and behaves exactly as it did under v1.2.
    "playlists": [],           # [{"id", "name", "folders": [path, ...]}]
    "favourites": [],          # [image path, ...] — non-destructive
    "hidden": [],              # [image path, ...] — non-destructive
    "playback_source": None,   # {"kind": "folder"|"playlist", "id": str} or None
    # v1.4 Power & Context Awareness — additive.
    "power": {"pause_on_battery_saver": True, "pause_on_fullscreen": True},
    "schedule": {"mode": "interval", "daily_times": []},  # mode: "interval"|"daily"
    # v1.5 Foundations for v2.0 — additive.
    "tags": {},           # {image path: [tag, ...]}
    "collections": [],    # [{"id", "name", "tags_any": [tag, ...]}]
    "solar": {             # data model only — not wired into playback yet (v2.0)
        "enabled": False,
        "latitude": None,
        "longitude": None,
        "fallback_times": ["06:00", "08:00", "18:00", "21:00"],  # dawn/day/dusk/night
    },
}

STARTUP_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE_NAME = "DesktopVista"

RECONNECT_POLL_MS = 15_000
POWER_POLL_MS = 5_000
DAILY_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
# SHQueryUserNotificationState values worth suppressing on: a fullscreen D3D
# app or a presentation is running. QUNS_BUSY/QUIET_TIME are deliberately
# excluded — those fire for ordinary foreground apps too often to be a
# useful "someone's watching the screen" signal.
FULLSCREEN_NOTIFICATION_STATES = frozenset({3, 4})  # D3D_FULL_SCREEN, PRESENTATION_MODE


# ---------------------------------------------------------------------------
# Pure / testable helpers (no Tk required)
# ---------------------------------------------------------------------------

def human_size(num_bytes: int) -> str:
    n = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def list_images(folder: str) -> list[str]:
    """Return sorted image paths in *folder*, or [] if unreadable."""
    try:
        return sorted(
            str(p)
            for p in Path(folder).iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        )
    except (OSError, ValueError) as exc:
        log.warning("Could not list images in %s: %s", folder, exc)
        return []


def is_folder_online(folder: str) -> bool:
    """Return True if *folder* currently exists and is a readable directory."""
    try:
        return Path(folder).is_dir()
    except OSError:
        return False


def folder_display_label(folder: str) -> str:
    """Decorate *folder* with an offline badge when its drive is unreachable."""
    return folder if is_folder_online(folder) else f"{folder}{OFFLINE_SUFFIX}"


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def find_playlist(cfg: dict, playlist_id: str) -> dict | None:
    return next((p for p in cfg.get("playlists", []) if p.get("id") == playlist_id), None)


def playlist_folder_status(playlist: dict) -> tuple[int, int]:
    """Return (online_count, total_count) for a playlist's member folders."""
    folders = playlist.get("folders", [])
    online = sum(1 for f in folders if is_folder_online(f))
    return online, len(folders)


def source_display_label(cfg: dict, kind: str, source_id: str) -> str:
    """Human-readable label for a folder, playlist, or collection source."""
    if kind == "playlist":
        playlist = find_playlist(cfg, source_id)
        if playlist is None:
            return f"(missing playlist {source_id})"
        online, total = playlist_folder_status(playlist)
        name = f"▶ {playlist.get('name', '(unnamed)')}"
        if total and online < total:
            return f"{name}  ({online}/{total} drives online)"
        return name
    if kind == "collection":
        collection = find_collection(cfg, source_id)
        if collection is None:
            return f"(missing collection {source_id})"
        return f"# {collection.get('name', '(unnamed)')}"
    return folder_display_label(source_id)


def find_collection(cfg: dict, collection_id: str) -> dict | None:
    return next((c for c in cfg.get("collections", []) if c.get("id") == collection_id), None)


def get_tags(cfg: dict, path: str) -> list[str]:
    return list(cfg.get("tags", {}).get(path, []))


def set_tags(cfg: dict, path: str, tags: list[str]) -> None:
    """Replace *path*'s tags (empty list removes its entry entirely)."""
    cleaned = dedupe_preserve_order([t.strip() for t in tags if t.strip()])
    tags_map = dict(cfg.get("tags", {}))
    if cleaned:
        tags_map[path] = cleaned
    else:
        tags_map.pop(path, None)
    cfg["tags"] = tags_map


def resolve_collection_candidate_images(cfg: dict, collection_id: str) -> list[str]:
    """
    Images from any known folder (standalone or inside a playlist) whose
    tags intersect the collection's tags_any. Hidden-filtering happens in
    resolve_source_images, uniformly across all source kinds.
    """
    collection = find_collection(cfg, collection_id)
    wanted = set(collection.get("tags_any", [])) if collection else set()
    if not wanted:
        return []
    tags_map = cfg.get("tags", {})
    all_folders = dedupe_preserve_order(
        list(cfg.get("folders", []))
        + [f for p in cfg.get("playlists", []) for f in p.get("folders", [])]
    )
    seen: set[str] = set()
    images: list[str] = []
    for folder in all_folders:
        for img in list_images(folder):
            if img not in seen and wanted & set(tags_map.get(img, [])):
                seen.add(img)
                images.append(img)
    return images


def resolve_source_images(cfg: dict, kind: str, source_id: str) -> list[str]:
    """
    Return the hidden-filtered image list for a folder, playlist, or
    tag-based collection source.

    Playlist images are the union of their member folders' images, folder
    order preserved, deduplicated (a folder listed twice contributes once).
    """
    if kind == "playlist":
        playlist = find_playlist(cfg, source_id)
        folders = playlist.get("folders", []) if playlist else []
        images: list[str] = []
        for folder in dedupe_preserve_order(folders):
            images.extend(list_images(folder))
        images = dedupe_preserve_order(images)
    elif kind == "collection":
        images = resolve_collection_candidate_images(cfg, source_id)
    else:
        images = list_images(source_id)
    hidden = set(cfg.get("hidden", []))
    return [img for img in images if img not in hidden]


def set_membership(cfg: dict, list_key: str, path: str, member: bool) -> None:
    """Add/remove *path* from cfg[list_key] (favourites/hidden), preserving order."""
    items = list(cfg.get(list_key, []))
    is_member = path in items
    if member and not is_member:
        items.append(path)
    elif not member and is_member:
        items.remove(path)
    cfg[list_key] = items


def is_valid_time_string(text: str) -> bool:
    return bool(DAILY_TIME_RE.match(text))


def parse_daily_time(text: str) -> tuple[int, int]:
    hour_str, minute_str = text.split(":")
    return int(hour_str), int(minute_str)


def next_daily_trigger(now: datetime, daily_times: list[str]) -> Optional[datetime]:
    """
    Return the soonest upcoming local trigger from a list of "HH:MM" times.

    Each time is evaluated independently against *now* (today if still
    ahead, otherwise tomorrow), then the earliest candidate wins. Recomputing
    from wall-clock "now" on every call — rather than caching a fixed future
    timestamp — is deliberate: it means a DST jump or system clock change
    between ticks self-corrects on the next call instead of drifting.
    """
    valid_times = [t for t in daily_times if is_valid_time_string(t)]
    if not valid_times:
        return None
    candidates = []
    for text in valid_times:
        hour, minute = parse_daily_time(text)
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        candidates.append(candidate)
    return min(candidates)


class _SystemPowerStatus(ctypes.Structure if ctypes is not None else object):
    _fields_ = (
        [
            ("ACLineStatus", ctypes.c_byte),
            ("BatteryFlag", ctypes.c_byte),
            ("BatteryLifePercent", ctypes.c_byte),
            ("SystemStatusFlag", ctypes.c_byte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]
        if ctypes is not None
        else []
    )


def get_power_status() -> Optional[dict]:
    """Return parsed GetSystemPowerStatus fields, or None if unavailable."""
    if ctypes is None or sys.platform != "win32":
        return None
    status = _SystemPowerStatus()
    try:
        ok = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
    except OSError:
        return None
    if not ok:
        return None
    return {
        "ac_line_status": status.ACLineStatus,  # 0=battery, 1=AC, 255=unknown
        "battery_life_percent": status.BatteryLifePercent,  # 0-100, 255=unknown
        # Bit 0 of SystemStatusFlag is the distinct "Battery Saver" toggle —
        # being on battery is not the same thing (notes_004 Track C).
        "battery_saver_on": bool(status.SystemStatusFlag & 1),
    }


def is_battery_saver_active(status: Optional[dict] = None) -> bool:
    """Pure predicate over a power-status dict — pass one explicitly in
    tests; real callers omit it to query the live GetSystemPowerStatus."""
    if status is None:
        status = get_power_status()
    return bool(status and status.get("battery_saver_on"))


def query_user_notification_state() -> Optional[int]:
    """Return the raw SHQueryUserNotificationState value, or None if unavailable."""
    if ctypes is None or sys.platform != "win32":
        return None
    state = ctypes.c_int(0)
    try:
        hresult = ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
    except OSError:
        return None
    return state.value if hresult == 0 else None  # 0 == S_OK


class _RECT(ctypes.Structure if ctypes is not None else object):
    _fields_ = (
        [
            ("left", ctypes.c_long), ("top", ctypes.c_long),
            ("right", ctypes.c_long), ("bottom", ctypes.c_long),
        ]
        if ctypes is not None
        else []
    )


class _MONITORINFOEXW(ctypes.Structure if ctypes is not None else object):
    _fields_ = (
        [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", _RECT),
            ("rcWork", _RECT),
            ("dwFlags", ctypes.c_ulong),
            ("szDevice", ctypes.c_wchar * 32),
        ]
        if ctypes is not None
        else []
    )


MONITORINFOF_PRIMARY = 0x1


def enumerate_monitors() -> list[dict]:
    """
    Read-only monitor topology via EnumDisplayMonitors/GetMonitorInfoW.

    Returns [{"device": str, "rect": (l, t, r, b), "primary": bool}, ...] in
    enumeration order, or [] on any non-Windows platform or API failure.
    This never writes anything — no wallpaper apply path reads it (yet);
    it exists purely so the UI can show the real arrangement (v1.5 P0).
    """
    if ctypes is None or sys.platform != "win32":
        return []
    monitors: list[dict] = []
    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(_RECT), ctypes.c_void_p
    )

    def _callback(hmonitor, _hdc, _lprect, _data):
        info = _MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(_MONITORINFOEXW)
        if ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            rect = info.rcMonitor
            monitors.append({
                "device": info.szDevice,
                "rect": (rect.left, rect.top, rect.right, rect.bottom),
                "primary": bool(info.dwFlags & MONITORINFOF_PRIMARY),
            })
        return 1  # non-zero: keep enumerating

    try:
        ctypes.windll.user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_callback), 0)
    except OSError:
        return []
    return monitors


def compute_topology_layout(monitors: list[dict], box_w: int, box_h: int) -> list[dict]:
    """
    Scale monitor rects to fit within box_w x box_h for display, preserving
    relative position and aspect ratio (uniform scale, union bounding box
    mapped to the box — same approach notes_004 Track B recommends for the
    real topology strip, so negative-coordinate/portrait arrangements still
    render sensibly).

    Returns each input monitor dict plus a "layout": {x, y, w, h} key in
    box-local pixel coordinates. Pure function — no live monitor query.
    """
    if not monitors or box_w <= 0 or box_h <= 0:
        return []
    lefts = [m["rect"][0] for m in monitors]
    tops = [m["rect"][1] for m in monitors]
    rights = [m["rect"][2] for m in monitors]
    bottoms = [m["rect"][3] for m in monitors]
    union_w = max(rights) - min(lefts)
    union_h = max(bottoms) - min(tops)
    if union_w <= 0 or union_h <= 0:
        return []
    scale = min(box_w / union_w, box_h / union_h)
    min_x, min_y = min(lefts), min(tops)
    out = []
    for m in monitors:
        l, t, r, b = m["rect"]
        out.append({
            **m,
            "layout": {
                "x": int((l - min_x) * scale),
                "y": int((t - min_y) * scale),
                "w": max(1, int((r - l) * scale)),
                "h": max(1, int((b - t) * scale)),
            },
        })
    return out


def is_fullscreen_active(state: Optional[int] = None) -> bool:
    """Pure predicate over a notification-state value — pass one explicitly
    in tests; real callers omit it to query the live Win32 API."""
    if state is None:
        state = query_user_notification_state()
    return state in FULLSCREEN_NOTIFICATION_STATES if state is not None else False


def resolve_interval_seconds(interval_key: str, custom_seconds: Any) -> int:
    """Resolve a slideshow interval selection (label or custom) to seconds."""
    if interval_key == CUSTOM_INTERVAL_LABEL:
        if (
            isinstance(custom_seconds, (int, float))
            and not isinstance(custom_seconds, bool)
            and math.isfinite(custom_seconds)
            and custom_seconds > 0
        ):
            return max(MIN_CUSTOM_INTERVAL_SECONDS, int(custom_seconds))
        return SLIDESHOW_INTERVALS["15 minutes"]
    return SLIDESHOW_INTERVALS.get(interval_key, SLIDESHOW_INTERVALS["15 minutes"])


def _validate_config(raw: dict) -> dict[str, Any]:
    """Coerce *raw* into a valid config dict, filling defaults where needed."""
    # Deep-copy: DEFAULT_CONFIG holds nested mutable values (e.g. "folders": []).
    # A shallow dict(DEFAULT_CONFIG) would share those objects, so a rejected
    # field (see the "folders" branch below) could leave cfg pointing straight
    # at the shared default, letting later in-place mutation (e.g. append)
    # contaminate DEFAULT_CONFIG itself for the rest of the process.
    cfg = copy.deepcopy(DEFAULT_CONFIG)

    folders = raw.get("folders", DEFAULT_CONFIG["folders"])
    if isinstance(folders, list) and all(isinstance(f, str) for f in folders):
        cfg["folders"] = list(folders)
    else:
        log.warning("Invalid 'folders' in config; using default.")

    current_folder = raw.get("current_folder", DEFAULT_CONFIG["current_folder"])
    if current_folder is None or isinstance(current_folder, str):
        cfg["current_folder"] = current_folder
    else:
        log.warning("Invalid 'current_folder' in config; using default.")

    current_image = raw.get("current_image", DEFAULT_CONFIG["current_image"])
    if current_image is None or isinstance(current_image, str):
        cfg["current_image"] = current_image
    else:
        log.warning("Invalid 'current_image' in config; using default.")

    style = raw.get("style", DEFAULT_CONFIG["style"])
    if isinstance(style, str) and style in WALLPAPER_STYLES:
        cfg["style"] = style
    else:
        log.warning("Invalid 'style' in config; using default.")

    interval = raw.get("interval", DEFAULT_CONFIG["interval"])
    if isinstance(interval, str) and (
        interval in SLIDESHOW_INTERVALS or interval == CUSTOM_INTERVAL_LABEL
    ):
        cfg["interval"] = interval
    else:
        log.warning("Invalid 'interval' in config; using default.")

    custom_seconds = raw.get("interval_custom_seconds", DEFAULT_CONFIG["interval_custom_seconds"])
    if custom_seconds is None:
        cfg["interval_custom_seconds"] = None
    elif (
        isinstance(custom_seconds, (int, float))
        and not isinstance(custom_seconds, bool)
        and math.isfinite(custom_seconds)
        and custom_seconds > 0
    ):
        cfg["interval_custom_seconds"] = int(custom_seconds)
    else:
        log.warning("Invalid 'interval_custom_seconds' in config; using default.")
        cfg["interval_custom_seconds"] = None

    shuffle = raw.get("shuffle", DEFAULT_CONFIG["shuffle"])
    if isinstance(shuffle, bool):
        cfg["shuffle"] = shuffle
    else:
        log.warning("Invalid 'shuffle' in config; using default.")

    tray = raw.get("tray", DEFAULT_CONFIG["tray"])
    if isinstance(tray, dict):
        tray_defaults = DEFAULT_CONFIG["tray"]
        # Require a literal bool for each flag — bool(value) would silently
        # accept "false" (truthy string) or 0/1 as if they were intentional.
        cfg["tray"] = {
            key: tray[key] if isinstance(tray.get(key), bool) else tray_defaults[key]
            for key in tray_defaults
        }
    else:
        log.warning("Invalid 'tray' in config; using default.")
        cfg["tray"] = dict(DEFAULT_CONFIG["tray"])

    # ---- v1.3 additions (all additive; absent/invalid -> safe defaults) ----

    playlists_raw = raw.get("playlists", [])
    valid_playlists: list[dict] = []
    seen_ids: set[str] = set()
    if isinstance(playlists_raw, list):
        for entry in playlists_raw:
            if not isinstance(entry, dict):
                continue
            pid, name, folders = entry.get("id"), entry.get("name"), entry.get("folders")
            if (
                isinstance(pid, str) and pid and pid not in seen_ids
                and isinstance(name, str) and name.strip()
                and isinstance(folders, list) and all(isinstance(f, str) for f in folders)
            ):
                seen_ids.add(pid)
                valid_playlists.append(
                    {"id": pid, "name": name, "folders": dedupe_preserve_order(folders)}
                )
            else:
                log.warning("Dropping invalid playlist entry in config: %r", entry)
    else:
        log.warning("Invalid 'playlists' in config; using default.")
    cfg["playlists"] = valid_playlists

    for list_key in ("favourites", "hidden"):
        raw_list = raw.get(list_key, [])
        if isinstance(raw_list, list) and all(isinstance(p, str) for p in raw_list):
            cfg[list_key] = dedupe_preserve_order(raw_list)
        else:
            log.warning("Invalid '%s' in config; using default.", list_key)
            cfg[list_key] = []

    playback_source = raw.get("playback_source")
    if (
        isinstance(playback_source, dict)
        and playback_source.get("kind") in ("folder", "playlist")
        and isinstance(playback_source.get("id"), str)
        and playback_source.get("id")
    ):
        kind, sid = playback_source["kind"], playback_source["id"]
        valid_ref = (
            (kind == "folder" and sid in cfg["folders"])
            or (kind == "playlist" and find_playlist(cfg, sid) is not None)
        )
        cfg["playback_source"] = {"kind": kind, "id": sid} if valid_ref else None
    else:
        cfg["playback_source"] = None

    # ---- v1.4 additions (all additive; absent/invalid -> safe defaults) ----

    power_raw = raw.get("power", DEFAULT_CONFIG["power"])
    if isinstance(power_raw, dict):
        power_defaults = DEFAULT_CONFIG["power"]
        cfg["power"] = {
            key: power_raw[key] if isinstance(power_raw.get(key), bool) else power_defaults[key]
            for key in power_defaults
        }
    else:
        log.warning("Invalid 'power' in config; using default.")
        cfg["power"] = dict(DEFAULT_CONFIG["power"])

    schedule_raw = raw.get("schedule", DEFAULT_CONFIG["schedule"])
    if isinstance(schedule_raw, dict):
        mode = schedule_raw.get("mode")
        daily_times_raw = schedule_raw.get("daily_times", [])
        valid_times = (
            [t for t in daily_times_raw if isinstance(t, str) and is_valid_time_string(t)]
            if isinstance(daily_times_raw, list)
            else []
        )
        cfg["schedule"] = {
            "mode": mode if mode in ("interval", "daily") else "interval",
            "daily_times": valid_times,
        }
    else:
        log.warning("Invalid 'schedule' in config; using default.")
        cfg["schedule"] = dict(DEFAULT_CONFIG["schedule"])

    # ---- v1.5 additions (all additive; absent/invalid -> safe defaults) ----

    tags_raw = raw.get("tags", {})
    valid_tags: dict[str, list[str]] = {}
    if isinstance(tags_raw, dict):
        for path, tag_list in tags_raw.items():
            if (
                isinstance(path, str)
                and isinstance(tag_list, list)
                and all(isinstance(t, str) for t in tag_list)
            ):
                cleaned = dedupe_preserve_order([t.strip() for t in tag_list if t.strip()])
                if cleaned:
                    valid_tags[path] = cleaned
    else:
        log.warning("Invalid 'tags' in config; using default.")
    cfg["tags"] = valid_tags

    collections_raw = raw.get("collections", [])
    valid_collections: list[dict] = []
    seen_collection_ids: set[str] = set()
    if isinstance(collections_raw, list):
        for entry in collections_raw:
            if not isinstance(entry, dict):
                continue
            cid, name, tags_any = entry.get("id"), entry.get("name"), entry.get("tags_any")
            if (
                isinstance(cid, str) and cid and cid not in seen_collection_ids
                and isinstance(name, str) and name.strip()
                and isinstance(tags_any, list) and all(isinstance(t, str) for t in tags_any)
                and tags_any
            ):
                seen_collection_ids.add(cid)
                valid_collections.append(
                    {"id": cid, "name": name, "tags_any": dedupe_preserve_order(tags_any)}
                )
            else:
                log.warning("Dropping invalid collection entry in config: %r", entry)
    else:
        log.warning("Invalid 'collections' in config; using default.")
    cfg["collections"] = valid_collections

    solar_raw = raw.get("solar", DEFAULT_CONFIG["solar"])
    if isinstance(solar_raw, dict):
        solar_defaults = DEFAULT_CONFIG["solar"]
        enabled = solar_raw.get("enabled")
        fallback_raw = solar_raw.get("fallback_times")
        valid_fallback = (
            [t for t in fallback_raw if isinstance(t, str) and is_valid_time_string(t)]
            if isinstance(fallback_raw, list) else []
        )
        if len(valid_fallback) != 4:
            valid_fallback = list(solar_defaults["fallback_times"])

        def _valid_coord(value: Any, bound: float) -> Optional[float]:
            if (
                isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and -bound <= value <= bound
            ):
                return float(value)
            return None

        cfg["solar"] = {
            "enabled": enabled if isinstance(enabled, bool) else solar_defaults["enabled"],
            "latitude": _valid_coord(solar_raw.get("latitude"), 90),
            "longitude": _valid_coord(solar_raw.get("longitude"), 180),
            "fallback_times": valid_fallback,
        }
    else:
        log.warning("Invalid 'solar' in config; using default.")
        cfg["solar"] = copy.deepcopy(DEFAULT_CONFIG["solar"])

    return cfg


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load and validate config from *path* (default CONFIG_PATH)."""
    cfg_path = path if path is not None else CONFIG_PATH
    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                log.warning("Config root is not an object; using defaults.")
                return dict(DEFAULT_CONFIG)
            return _validate_config(raw)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not read config (%s); using defaults.", exc)
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict, path: Path | None = None) -> None:
    """Atomically write *cfg* to *path* via a unique temporary sibling file."""
    cfg_path = path if path is not None else CONFIG_PATH
    # A fixed ".tmp" name would let two instances (or a smoke-test script
    # relaunched quickly) race on the same temp file; mkstemp guarantees a
    # unique name per call.
    fd, tmp_name = tempfile.mkstemp(
        prefix=cfg_path.stem + ".", suffix=".tmp", dir=str(cfg_path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        data = json.dumps(cfg, indent=2)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp_path, cfg_path)
    except OSError as exc:
        log.error("Could not save config: %s", exc)
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass


def cache_dir() -> Path:
    """Return (and create) the wallpaper transcode cache directory."""
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    d = Path(base) / "DesktopVista" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def wallpaper_cache_key(source: Path) -> str:
    """Stable hash key from path + mtime + size."""
    try:
        st = source.stat()
        payload = f"{source.resolve()}|{st.st_mtime_ns}|{st.st_size}"
    except OSError:
        payload = str(source)
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:32]


def ensure_wallpaper_path(
    path: str,
    cache_root: Path | None = None,
) -> str:
    """
    Return a path suitable for SystemParametersInfoW.

    Native formats (.jpg/.jpeg/.bmp/.png) are returned unchanged.
    Others (e.g. WebP) are transcoded to a JPEG under the cache directory,
    keyed by source path + mtime + size. EXIF orientation is applied.
    """
    src = Path(path)
    if src.suffix.lower() in NATIVE_WALLPAPER_EXTS:
        return str(src)

    root = cache_root if cache_root is not None else cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    out = root / f"{wallpaper_cache_key(src)}.jpg"
    if out.is_file():
        return str(out)

    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        elif im.mode == "L":
            im = im.convert("RGB")
        im.save(out, format="JPEG", quality=95)
    log.info("Transcoded %s -> %s", src.name, out)
    return str(out)


def build_shuffle_deck(n: int, current: int = -1) -> list[int]:
    """
    Fisher–Yates shuffle of indices ``0..n-1``.

    If *current* is a valid index and ``n > 1``, it is placed so that the
    first draw skips the current image (current moved to the end, then
    remaining prefix is shuffled — actually: shuffle all, then if the first
    element is *current*, swap with another). Simpler approach used here:
    shuffle all indices, then if the deck starts with *current*, rotate it
    to the end so the first pop skips it.
    """
    if n <= 0:
        return []
    deck = list(range(n))
    # Fisher–Yates
    for i in range(n - 1, 0, -1):
        j = random.randint(0, i)
        deck[i], deck[j] = deck[j], deck[i]
    if n > 1 and 0 <= current < n and deck and deck[0] == current:
        # Move current to the end so the next draw is not the same image.
        deck.append(deck.pop(0))
    return deck


def set_windows_wallpaper(path: str, style: str) -> None:
    """Apply a wallpaper and its fit style. Windows only."""
    if sys.platform != "win32":
        raise RuntimeError("Desktop Vista only sets wallpapers on Windows.")
    if winreg is None or ctypes is None:
        raise RuntimeError("Windows APIs (winreg/ctypes) are unavailable.")

    apply_path = ensure_wallpaper_path(path)
    wp_style, tile = WALLPAPER_STYLES.get(style, WALLPAPER_STYLES["Fill"])
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, wp_style)
        winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, tile)

    SPI_SETDESKWALLPAPER = 0x0014
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02
    ok = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER, 0, apply_path, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    )
    if not ok:
        raise ctypes.WinError()


def build_startup_command(python_exe: str, script_path: str) -> str:
    """
    Build the Run-key command line to relaunch Desktop Vista minimised.

    In a frozen build, *python_exe* (``sys.executable``) already *is*
    DesktopVista.exe, so it's invoked directly with no script argument.
    Otherwise prefers ``pythonw.exe`` beside *python_exe* (no console flash
    on login), falling back to *python_exe* itself if that's not present.
    """
    if FROZEN:
        return f'"{python_exe}" --minimized'
    exe = python_exe
    pythonw = Path(python_exe).with_name("pythonw.exe")
    if pythonw.is_file():
        exe = str(pythonw)
    return f'"{exe}" "{script_path}" --minimized'


def is_startup_enabled() -> bool:
    """
    Return True if the Run-key entry exists AND still matches the command
    this install would write today.

    A stale entry (Python moved/upgraded, script relocated) is reported as
    disabled rather than a false "on" that the toggle can't actually turn
    off cleanly — flipping it re-registers the current, correct command.
    """
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, STARTUP_KEY_PATH, 0, winreg.KEY_READ
        ) as key:
            value, _ = winreg.QueryValueEx(key, STARTUP_VALUE_NAME)
    except OSError:
        return False
    expected = build_startup_command(sys.executable, str(APP_DIR / "desktop_vista.py"))
    return value == expected


def set_startup_enabled(enabled: bool) -> None:
    """Create or remove the Desktop Vista Run-key startup entry."""
    if winreg is None:
        raise RuntimeError("Windows registry (winreg) is unavailable.")
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, STARTUP_KEY_PATH, 0, winreg.KEY_SET_VALUE
    ) as key:
        if enabled:
            command = build_startup_command(sys.executable, str(APP_DIR / "desktop_vista.py"))
            winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, STARTUP_VALUE_NAME)
            except FileNotFoundError:
                pass


def _load_preview_image(path: str, max_w: int, max_h: int) -> tuple[Image.Image, int, int]:
    """Open *path*, apply EXIF transpose, thumbnail to max box. Returns (rgb, w, h)."""
    with Image.open(path) as im:
        width, height = im.size
        # Read orientation before draft(): draft() can decide to load pixels
        # at a reduced size immediately, and calling exif_transpose()
        # afterwards would then rotate a box already sized for the
        # un-rotated image — request draft with the box swapped for a 90°
        # rotation so the fast reduced decode still lands close to target.
        rotated = im.getexif().get(274, 1) in (5, 6, 7, 8)
        draft_box = (max_h, max_w) if rotated else (max_w, max_h)
        im.draft("RGB", draft_box)
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        im.thumbnail((max_w, max_h), Image.LANCZOS)
        # Copy pixels out of the context manager
        out = im.copy()
    if rotated:
        width, height = height, width
    return out, width, height


def build_tray_icon_image(size: int = 64) -> Image.Image:
    """
    Procedural placeholder tray icon: a minimalist framed 16:9 landscape.

    Stands in for the branded .ico (v1.2 P2, notes_001 concepts) until that
    asset exists — keeps the tray feature unblocked by icon design work.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = max(size // 8, 2)
    frame = (margin, margin, size - margin, size - margin)
    draw.rounded_rectangle(frame, radius=max(size // 10, 2), outline=(58, 141, 222, 255),
                            width=max(size // 16, 2))
    horizon_y = margin + int((frame[3] - frame[1]) * 0.62)
    draw.line((frame[0] + 2, horizon_y, frame[2] - 2, horizon_y),
              fill=(58, 141, 222, 255), width=max(size // 24, 1))
    peak_h = int((frame[3] - frame[1]) * 0.32)
    base_y = horizon_y
    peak_x = frame[0] + int((frame[2] - frame[0]) * 0.38)
    draw.polygon(
        [
            (frame[0] + int((frame[2] - frame[0]) * 0.18), base_y),
            (peak_x, base_y - peak_h),
            (frame[0] + int((frame[2] - frame[0]) * 0.58), base_y),
        ],
        fill=(58, 141, 222, 255),
    )
    return img


def load_brand_icon(size: int = 64) -> Image.Image:
    """Load the supplied Desktop Vista glyph for the tray; fall back to the
    procedural placeholder if the asset is missing or unreadable."""
    try:
        with Image.open(BRAND_ICON_PATH) as source:
            result = source.convert("RGBA")
        result.thumbnail((size, size), Image.LANCZOS)
        return result
    except (OSError, ValueError):
        log.warning("Brand icon unavailable; using fallback", exc_info=True)
        return build_tray_icon_image(size)


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class DesktopVista(ctk.CTk):
    def __init__(self, start_minimized: bool = False) -> None:
        super().__init__()
        self._start_minimized = start_minimized
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME}  —  {TAGLINE}")
        self.geometry("1180x620")
        self.minsize(980, 560)

        self.cfg = load_config()
        self.images: list[str] = []
        self.index: int = -1
        self._active_kind: str = "folder"
        self._active_id: Optional[str] = None
        self._source_label_to_key: dict[str, tuple[str, str]] = {}
        self._reconnect_job: Any = None
        # "Running" reflects user intent (Start/Stop Slideshow); _slideshow_job
        # is only the currently-scheduled tick, which auto-pause cancels
        # without touching intent — the two can legitimately disagree while
        # paused for battery/fullscreen, and the monitor tick below acts on
        # exactly that gap to resume once the reason clears.
        self._slideshow_running: bool = False
        self._auto_pause_reasons: set[str] = set()
        self._power_job: Any = None
        self._preview_ref = None  # keep CTkImage alive
        self._slideshow_job: Any = None
        self._save_job: Any = None
        self._shuffle_order: list[int] = []
        self._shuffle_cursor: int = 0
        self._load_token: int = 0
        self._preview_size: tuple[int, int] = (PREVIEW_W, PREVIEW_H)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dv-img")
        self._closing = False
        self.tray_icon: Any = None
        self._tray_thread: Optional[threading.Thread] = None
        self._tray_ready: Optional[threading.Event] = None
        self._tray_failed = False

        self._build_ui()
        self._apply_window_icon()
        # CustomTkinter sets its own default window icon shortly after
        # construction on Windows; re-apply ours once that has had a chance
        # to run so the branded icon isn't silently overwritten.
        self.after(300, self._apply_window_icon)
        self._restore_state()
        self.protocol("WM_DELETE_WINDOW", self._on_close_request)
        self._init_tray()
        self._sync_startup_state()
        self._start_reconnect_watcher()
        self._start_power_monitor()
        if self._start_minimized:
            if self._tray_is_ready():
                self.withdraw()
            else:
                log.warning(
                    "--minimized requested but the tray icon isn't ready; showing window."
                )

    # ---------------- UI construction ----------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---- Left sidebar: scrollable control panel ----
        # A CTkScrollableFrame rather than a fixed-height CTkFrame: v1.3+
        # keeps adding sections (playlists, and later power/schedule,
        # monitor topology) and a fixed sidebar would either clip them or
        # force renumbering every row index each time. `row()` hands out
        # sequential grid rows so new sections just call it again.
        side = ctk.CTkScrollableFrame(self, width=300, corner_radius=12)
        side.grid(row=0, column=0, sticky="nsw", padx=(12, 6), pady=12)
        side.grid_columnconfigure(0, weight=1)
        self._sidebar_row = 0

        def row() -> int:
            r = self._sidebar_row
            self._sidebar_row += 1
            return r

        ctk.CTkLabel(side, text=APP_NAME, font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=row(), column=0, padx=16, pady=(16, 0), sticky="w")
        ctk.CTkLabel(side, text=TAGLINE, font=ctk.CTkFont(size=12), text_color="gray70").grid(
            row=row(), column=0, padx=16, pady=(0, 14), sticky="w")

        # Playback source: folders and playlists share one dropdown — the
        # active source, whichever kind it is, drives preview/nav/slideshow.
        ctk.CTkLabel(side, text="PLAYBACK SOURCE", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray60").grid(row=row(), column=0, padx=16, sticky="w")
        self.source_var = ctk.StringVar(value="(no sources yet)")
        self.source_menu = ctk.CTkOptionMenu(
            side, variable=self.source_var, values=["(no sources yet)"],
            command=self._on_source_selected, dynamic_resizing=False)
        self.source_menu.grid(row=row(), column=0, padx=16, pady=(4, 6), sticky="ew")

        fbtns = ctk.CTkFrame(side, fg_color="transparent")
        fbtns.grid(row=row(), column=0, padx=16, sticky="ew")
        fbtns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(fbtns, text="+ Add folder", command=self._add_folder).grid(
            row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(fbtns, text="Remove", fg_color="gray30", hover_color="gray25",
                      command=self._remove_folder).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # Playlists: named groups of folders, aggregated as one source.
        ctk.CTkLabel(side, text="PLAYLISTS", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray60").grid(row=row(), column=0, padx=16, pady=(14, 0), sticky="w")
        ctk.CTkButton(side, text="+ New Playlist",
                      command=lambda: self._open_playlist_editor()).grid(
            row=row(), column=0, padx=16, pady=(4, 4), sticky="ew")
        pbtns = ctk.CTkFrame(side, fg_color="transparent")
        pbtns.grid(row=row(), column=0, padx=16, sticky="ew")
        pbtns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(pbtns, text="Edit", fg_color="gray30", hover_color="gray25",
                      command=self._edit_active_playlist).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(pbtns, text="Delete", fg_color="gray30", hover_color="gray25",
                      command=self._delete_active_playlist).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # Collections: saved tag filters, spanning any tagged image cross-drive.
        ctk.CTkLabel(side, text="COLLECTIONS", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray60").grid(row=row(), column=0, padx=16, pady=(14, 0), sticky="w")
        ctk.CTkButton(side, text="+ New Collection",
                      command=lambda: self._open_collection_editor()).grid(
            row=row(), column=0, padx=16, pady=(4, 4), sticky="ew")
        cbtns = ctk.CTkFrame(side, fg_color="transparent")
        cbtns.grid(row=row(), column=0, padx=16, sticky="ew")
        cbtns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(cbtns, text="Edit", fg_color="gray30", hover_color="gray25",
                      command=self._edit_active_collection).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(cbtns, text="Delete", fg_color="gray30", hover_color="gray25",
                      command=self._delete_active_collection).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # Fit style
        ctk.CTkLabel(side, text="FIT STYLE", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray60").grid(row=row(), column=0, padx=16, pady=(18, 0), sticky="w")
        self.style_var = ctk.StringVar(value=self.cfg["style"])
        ctk.CTkOptionMenu(side, variable=self.style_var, values=list(WALLPAPER_STYLES),
                          command=self._on_style_changed).grid(
            row=row(), column=0, padx=16, pady=(4, 0), sticky="ew")

        # Primary action
        self.set_btn = ctk.CTkButton(
            side, text="Set as Wallpaper", height=44,
            font=ctk.CTkFont(size=15, weight="bold"), command=self._set_wallpaper)
        self.set_btn.grid(row=row(), column=0, padx=16, pady=(22, 0), sticky="ew")

        # Slideshow
        ctk.CTkLabel(side, text="SLIDESHOW", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray60").grid(row=row(), column=0, padx=16, pady=(24, 0), sticky="w")
        self.interval_var = ctk.StringVar(value=self.cfg["interval"])
        ctk.CTkOptionMenu(side, variable=self.interval_var,
                          values=list(SLIDESHOW_INTERVALS) + [CUSTOM_INTERVAL_LABEL],
                          command=self._on_interval_changed).grid(
            row=row(), column=0, padx=16, pady=(4, 6), sticky="ew")
        self.shuffle_var = ctk.BooleanVar(value=self.cfg["shuffle"])
        ctk.CTkSwitch(side, text="Shuffle", variable=self.shuffle_var,
                      command=self._on_shuffle_changed).grid(row=row(), column=0, padx=16, sticky="w")
        self.slide_btn = ctk.CTkButton(
            side, text="Start Slideshow", height=40, fg_color="#2e7d32", hover_color="#27682a",
            command=self._toggle_slideshow)
        self.slide_btn.grid(row=row(), column=0, padx=16, pady=(12, 0), sticky="ew")

        # Power & schedule
        ctk.CTkLabel(side, text="POWER & SCHEDULE", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray60").grid(row=row(), column=0, padx=16, pady=(24, 0), sticky="w")
        self.battery_pause_var = ctk.BooleanVar(value=self.cfg["power"]["pause_on_battery_saver"])
        ctk.CTkSwitch(side, text="Pause on Battery Saver", variable=self.battery_pause_var,
                      command=self._on_power_settings_changed).grid(
            row=row(), column=0, padx=16, pady=(4, 0), sticky="w")
        self.fullscreen_pause_var = ctk.BooleanVar(value=self.cfg["power"]["pause_on_fullscreen"])
        ctk.CTkSwitch(side, text="Pause during fullscreen/games", variable=self.fullscreen_pause_var,
                      command=self._on_power_settings_changed).grid(
            row=row(), column=0, padx=16, pady=(4, 6), sticky="w")
        self.schedule_mode_var = ctk.StringVar(
            value="Daily times" if self.cfg["schedule"]["mode"] == "daily" else "Fixed interval")
        ctk.CTkOptionMenu(side, variable=self.schedule_mode_var,
                          values=["Fixed interval", "Daily times"],
                          command=self._on_schedule_mode_changed).grid(
            row=row(), column=0, padx=16, pady=(0, 4), sticky="ew")
        self.daily_times_var = ctk.StringVar(value=", ".join(self.cfg["schedule"]["daily_times"]))
        self.daily_times_entry = ctk.CTkEntry(
            side, textvariable=self.daily_times_var, placeholder_text="e.g. 08:00, 18:00")
        self.daily_times_entry.grid(row=row(), column=0, padx=16, sticky="ew")
        ctk.CTkButton(side, text="Apply times", fg_color="gray30", hover_color="gray25",
                      command=self._on_daily_times_apply).grid(
            row=row(), column=0, padx=16, pady=(4, 0), sticky="ew")

        # Monitor topology (read-only; v1.5 groundwork — no per-monitor apply yet)
        ctk.CTkLabel(side, text="MONITORS (read-only)", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray60").grid(row=row(), column=0, padx=16, pady=(24, 0), sticky="w")
        self.monitor_canvas = Canvas(side, width=260, height=80, highlightthickness=0, bg="#2b2b2b")
        self.monitor_canvas.grid(row=row(), column=0, padx=16, pady=(4, 0), sticky="ew")
        ctk.CTkButton(side, text="Refresh", fg_color="gray30", hover_color="gray25", width=80,
                      command=self._refresh_monitor_topology).grid(
            row=row(), column=0, padx=16, pady=(4, 0), sticky="w")
        self._refresh_monitor_topology()

        # Startup
        ctk.CTkLabel(side, text="STARTUP", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray60").grid(row=row(), column=0, padx=16, pady=(24, 0), sticky="w")
        self.startup_var = ctk.BooleanVar(value=False)
        self.startup_switch = ctk.CTkSwitch(
            side, text="Start with Windows (minimised)", variable=self.startup_var,
            command=self._on_startup_toggle)
        self.startup_switch.grid(row=row(), column=0, padx=16, pady=(4, 0), sticky="w")
        if winreg is None or sys.platform != "win32":
            self.startup_switch.configure(state="disabled")

        # Status
        self.status = ctk.CTkLabel(side, text="Ready.", text_color="gray60",
                                   font=ctk.CTkFont(size=11), wraplength=260, justify="left")
        self.status.grid(row=row(), column=0, padx=16, pady=(20, 14), sticky="w")

        # ---- Right main area: the canvas ----
        self.main = ctk.CTkFrame(self, corner_radius=12)
        self.main.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

        self.preview = ctk.CTkLabel(self.main, text="Add a folder to begin", text_color="gray50",
                                    font=ctk.CTkFont(size=16))
        self.preview.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="nsew")

        self.meta = ctk.CTkLabel(self.main, text="", text_color="gray60", font=ctk.CTkFont(size=12))
        self.meta.grid(row=1, column=0, padx=16, sticky="ew")

        nav = ctk.CTkFrame(self.main, fg_color="transparent")
        nav.grid(row=2, column=0, pady=(8, 4))
        ctk.CTkButton(nav, text="◀  Previous", width=130, command=self._prev).grid(row=0, column=0, padx=6)
        ctk.CTkButton(nav, text="Random", width=110, fg_color="gray30", hover_color="gray25",
                      command=self._random).grid(row=0, column=1, padx=6)
        ctk.CTkButton(nav, text="Next  ▶", width=130, command=self._next).grid(row=0, column=2, padx=6)

        # Favourite / hide — non-destructive curation of the active source
        curate = ctk.CTkFrame(self.main, fg_color="transparent")
        curate.grid(row=3, column=0, pady=(0, 16))
        self.fav_btn = ctk.CTkButton(curate, text="♡ Favourite", width=130, fg_color="gray30",
                                      hover_color="gray25", command=self._toggle_favourite)
        self.fav_btn.grid(row=0, column=0, padx=6)
        ctk.CTkButton(curate, text="🙈 Hide", width=110, fg_color="gray30", hover_color="gray25",
                      command=self._hide_current).grid(row=0, column=1, padx=6)
        self.hidden_btn = ctk.CTkButton(curate, text="Hidden (0)", width=130, fg_color="gray30",
                                         hover_color="gray25", command=self._open_hidden_manager)
        self.hidden_btn.grid(row=0, column=2, padx=6)

        # Tags — freeform per-image labels; collections filter playback by these
        tagrow = ctk.CTkFrame(self.main, fg_color="transparent")
        tagrow.grid(row=4, column=0, pady=(0, 16))
        ctk.CTkLabel(tagrow, text="Tags:").grid(row=0, column=0, padx=(0, 6))
        self.tags_var = ctk.StringVar(value="")
        self.tags_entry = ctk.CTkEntry(tagrow, textvariable=self.tags_var, width=220,
                                        placeholder_text="nature, minimal")
        self.tags_entry.grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(tagrow, text="Apply", width=70, command=self._on_tags_apply).grid(
            row=0, column=2)

        # Keyboard shortcuts
        self.bind("<Left>", lambda e: self._prev())
        self.bind("<Right>", lambda e: self._next())
        self.bind("<Return>", lambda e: self._set_wallpaper())
        self.bind("<space>", lambda e: self._next())
        self.bind("<BackSpace>", lambda e: self._prev())
        self.bind("p", lambda e: self._prev())
        self.bind("<Escape>", lambda e: self._stop_slideshow())
        self.bind("r", lambda e: self._random())
        self.bind("R", lambda e: self._random())
        self.bind("f", lambda e: self._toggle_favourite())
        self.bind("F", lambda e: self._toggle_favourite())
        self.bind("h", lambda e: self._hide_current())

        # Dynamic 16:9 preview sizing
        self.preview.bind("<Configure>", self._on_preview_configure)
        self.main.bind("<Configure>", self._on_preview_configure)

    # ---------------- Branding ----------------

    def _apply_window_icon(self) -> None:
        if sys.platform != "win32" or not BRAND_ICON_PATH.is_file():
            return
        try:
            self.iconbitmap(str(BRAND_ICON_PATH))
        except Exception as exc:
            log.warning("Could not set window icon: %s", exc)

    # ---------------- Monitor topology (read-only) ----------------

    def _refresh_monitor_topology(self) -> None:
        monitors = enumerate_monitors()
        canvas = self.monitor_canvas
        canvas.delete("all")
        box_w = int(canvas["width"])
        box_h = int(canvas["height"])
        if not monitors:
            canvas.create_text(box_w // 2, box_h // 2, text="Unavailable", fill="gray60")
            return
        margin = 4
        layout = compute_topology_layout(monitors, box_w - 2 * margin, box_h - 2 * margin)
        for i, monitor in enumerate(layout, start=1):
            box = monitor["layout"]
            x0, y0 = margin + box["x"], margin + box["y"]
            x1, y1 = x0 + box["w"], y0 + box["h"]
            color = "#3a8dde" if monitor["primary"] else "#5a5a5a"
            canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="#1c1c1c")
            label = f"{i}" + (" ★" if monitor["primary"] else "")
            canvas.create_text(
                (x0 + x1) // 2, (y0 + y1) // 2, text=label, fill="white",
                font=("Segoe UI", 9, "bold"),
            )

    # ---------------- Debounced save ----------------

    def _schedule_save(self) -> None:
        """Debounce config writes (SAVE_DEBOUNCE_MS)."""
        if self._save_job is not None:
            try:
                self.after_cancel(self._save_job)
            except Exception:
                pass
            self._save_job = None
        self._save_job = self.after(SAVE_DEBOUNCE_MS, self._flush_save)

    def _flush_save(self) -> None:
        """Write config immediately; cancel any pending debounce."""
        if self._save_job is not None:
            try:
                self.after_cancel(self._save_job)
            except Exception:
                pass
            self._save_job = None
        self._write_config()

    def _write_config(self) -> None:
        self.cfg["style"] = self.style_var.get()
        self.cfg["interval"] = self.interval_var.get()
        self.cfg["shuffle"] = bool(self.shuffle_var.get())
        self.cfg["current_image"] = (
            self.images[self.index] if 0 <= self.index < len(self.images) else None
        )
        save_config(self.cfg)

    def _save(self, *_args) -> None:
        """Public save entry — schedules a debounced write."""
        self._schedule_save()

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)

    # ---------------- State ----------------

    def _resolve_initial_source(self) -> Optional[tuple[str, str]]:
        """Pick which source to load on startup: the saved playback_source,
        falling back to legacy current_folder, then the first known folder
        or playlist, in that order of preference."""
        ps = self.cfg.get("playback_source")
        if ps:
            kind, sid = ps["kind"], ps["id"]
            if kind == "folder" and sid in self.cfg["folders"]:
                return kind, sid
            if kind == "playlist" and find_playlist(self.cfg, sid) is not None:
                return kind, sid
        current_folder = self.cfg.get("current_folder")
        if current_folder and current_folder in self.cfg["folders"]:
            return "folder", current_folder
        if self.cfg["folders"]:
            return "folder", self.cfg["folders"][0]
        if self.cfg["playlists"]:
            return "playlist", self.cfg["playlists"][0]["id"]
        if self.cfg["collections"]:
            return "collection", self.cfg["collections"][0]["id"]
        return None

    def _restore_state(self) -> None:
        """Load the saved source without showing, then restore last image and show once."""
        initial = self._resolve_initial_source()
        if initial is None:
            self._refresh_source_menu()
            return
        kind, source_id = initial
        self._load_source(kind, source_id, show=False)
        last = self.cfg.get("current_image")
        if last in self.images:
            self.index = self.images.index(last)
        elif self.images:
            self.index = 0
        if self.images:
            self._show_current()
        else:
            self._flush_save()

    # ---------------- Playback source: folders + playlists ----------------

    def _refresh_source_menu(self) -> None:
        """Rebuild the source dropdown (folders + playlists), badging
        offline folders/playlists without user action."""
        labels: list[str] = []
        mapping: dict[str, tuple[str, str]] = {}
        for folder in self.cfg["folders"]:
            label = folder_display_label(folder)
            labels.append(label)
            mapping[label] = ("folder", folder)
        for playlist in self.cfg["playlists"]:
            label = source_display_label(self.cfg, "playlist", playlist["id"])
            labels.append(label)
            mapping[label] = ("playlist", playlist["id"])
        for collection in self.cfg["collections"]:
            label = source_display_label(self.cfg, "collection", collection["id"])
            labels.append(label)
            mapping[label] = ("collection", collection["id"])
        self._source_label_to_key = mapping

        if not labels:
            self.source_menu.configure(values=["(no sources yet)"])
            self.source_var.set("(no sources yet)")
            return

        self.source_menu.configure(values=labels)
        current_label = next(
            (
                label for label, (kind, sid) in mapping.items()
                if kind == self._active_kind and sid == self._active_id
            ),
            None,
        )
        # Active source no longer exists (deleted/renamed elsewhere) — the
        # dropdown must still show something valid.
        self.source_var.set(current_label if current_label is not None else labels[0])

    def _on_source_selected(self, label: str) -> None:
        key = self._source_label_to_key.get(label)
        if key is not None:
            self._load_source(*key)

    def _load_source(self, kind: str, source_id: str, show: bool = True) -> None:
        self._flush_save()  # persist the previous source/image before switching
        # Invalidate any in-flight preview load from the previous source
        # immediately, even if this one turns out to have no images —
        # otherwise a late callback for the old source could still land and
        # repaint over the "No images found" / offline status text.
        self._load_token += 1
        self._active_kind, self._active_id = kind, source_id
        self.cfg["playback_source"] = {"kind": kind, "id": source_id}
        if kind == "folder":
            self.cfg["current_folder"] = source_id  # kept in sync for v1.2 readers
        self._refresh_source_menu()
        self.images = resolve_source_images(self.cfg, kind, source_id)
        self._shuffle_order = []
        self._shuffle_cursor = 0
        if not self.images:
            self.index = -1
            if show:
                self.preview.configure(image=None, text="No images found in this source")
                self.meta.configure(text="")
                self._update_favourite_button()
                self._update_tags_field()
            if kind == "folder" and not is_folder_online(source_id):
                self._set_status("Folder is offline (drive disconnected?).")
            elif kind == "playlist":
                playlist = find_playlist(self.cfg, source_id)
                online, total = playlist_folder_status(playlist) if playlist else (0, 0)
                if total and online == 0:
                    self._set_status("All folders in this playlist are offline.")
                else:
                    self._set_status("No images found in this playlist.")
            elif kind == "collection":
                self._set_status("No images match this collection's tags.")
            else:
                self._set_status("No images found in this folder.")
            self._flush_save()
            if self._slideshow_running:
                self._stop_slideshow()
            return

        self.index = 0
        noun = {"playlist": "playlist", "collection": "collection"}.get(kind, "folder")
        if kind == "playlist":
            name = find_playlist(self.cfg, source_id)["name"]
        elif kind == "collection":
            name = find_collection(self.cfg, source_id)["name"]
        else:
            name = Path(source_id).name or source_id
        self._set_status(f"{len(self.images)} images in {noun} '{name}'")
        if show:
            self._show_current()
        else:
            self._flush_save()

    def _add_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Choose a wallpaper folder")
        if not chosen:
            return
        chosen = os.path.normpath(chosen)
        if chosen not in self.cfg["folders"]:
            self.cfg["folders"].append(chosen)
        self._load_source("folder", chosen)

    def _remove_folder(self) -> None:
        if self._active_kind != "folder" or self._active_id not in self.cfg["folders"]:
            self._set_status("Select a folder (not a playlist) to remove it.")
            return
        folder = self._active_id
        if not messagebox.askyesno(
            APP_NAME,
            f"Remove this folder from Desktop Vista?\n\n{folder}\n\n(No files are deleted.)",
        ):
            return
        self._stop_slideshow()
        self.cfg["folders"].remove(folder)
        # A playlist referencing this folder can no longer resolve it —
        # drop the reference rather than leave a dangling path behind.
        for playlist in self.cfg["playlists"]:
            if folder in playlist["folders"]:
                playlist["folders"] = [f for f in playlist["folders"] if f != folder]

        fallback = self._resolve_initial_source()
        if fallback:
            self._load_source(*fallback)
        else:
            self._load_token += 1
            self.images, self.index = [], -1
            self._active_kind, self._active_id = "folder", None
            self.cfg["current_folder"] = None
            self.cfg["current_image"] = None
            self.cfg["playback_source"] = None
            self._refresh_source_menu()
            self.preview.configure(image=None, text="Add a folder to begin")
            self.meta.configure(text="")
            self._flush_save()

    # ---------------- Playlists ----------------

    def _open_playlist_editor(self, playlist: Optional[dict] = None) -> None:
        """Modal editor for creating or renaming/re-scoping a playlist."""
        win = ctk.CTkToplevel(self)
        win.title("New Playlist" if playlist is None else f"Edit Playlist — {playlist['name']}")
        win.geometry("420x480")
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text="Playlist name").pack(padx=16, pady=(16, 4), anchor="w")
        name_var = ctk.StringVar(value=playlist["name"] if playlist else "")
        ctk.CTkEntry(win, textvariable=name_var).pack(padx=16, fill="x")

        ctk.CTkLabel(win, text="Folders to include").pack(padx=16, pady=(16, 4), anchor="w")
        scroll = ctk.CTkScrollableFrame(win, height=260)
        scroll.pack(padx=16, pady=(0, 8), fill="both", expand=True)
        existing = set(playlist["folders"]) if playlist else set()
        check_vars: dict[str, ctk.BooleanVar] = {}
        for folder in self.cfg["folders"]:
            var = ctk.BooleanVar(value=folder in existing)
            ctk.CTkCheckBox(scroll, text=folder_display_label(folder), variable=var).pack(
                anchor="w", pady=2, padx=4
            )
            check_vars[folder] = var
        if not self.cfg["folders"]:
            ctk.CTkLabel(scroll, text="Add a wallpaper folder first.",
                         text_color="gray60").pack(pady=8)

        def do_save() -> None:
            name = name_var.get().strip()
            chosen = [f for f, v in check_vars.items() if v.get()]
            if not name:
                messagebox.showerror(APP_NAME, "Playlist needs a name.", parent=win)
                return
            if not chosen:
                messagebox.showerror(APP_NAME, "Select at least one folder.", parent=win)
                return
            if playlist is None:
                created = {"id": new_id(), "name": name, "folders": chosen}
                self.cfg["playlists"].append(created)
                self._load_source("playlist", created["id"])
            else:
                playlist["name"] = name
                playlist["folders"] = chosen
                if self._active_kind == "playlist" and self._active_id == playlist["id"]:
                    self._load_source("playlist", playlist["id"])
                else:
                    self._refresh_source_menu()
            self._flush_save()
            win.destroy()

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(padx=16, pady=12, fill="x")
        ctk.CTkButton(btns, text="Save", command=do_save).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(btns, text="Cancel", fg_color="gray30", hover_color="gray25",
                      command=win.destroy).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _edit_active_playlist(self) -> None:
        if self._active_kind != "playlist":
            self._set_status("Select a playlist to edit.")
            return
        playlist = find_playlist(self.cfg, self._active_id)
        if playlist is not None:
            self._open_playlist_editor(playlist)

    def _delete_active_playlist(self) -> None:
        if self._active_kind != "playlist":
            self._set_status("Select a playlist to delete.")
            return
        playlist = find_playlist(self.cfg, self._active_id)
        if playlist is None:
            return
        if not messagebox.askyesno(
            APP_NAME,
            f"Delete playlist '{playlist['name']}'?\n\n(No image files are deleted.)",
        ):
            return
        self._stop_slideshow()
        self.cfg["playlists"] = [p for p in self.cfg["playlists"] if p["id"] != playlist["id"]]
        if self.cfg.get("playback_source") and self.cfg["playback_source"]["id"] == playlist["id"]:
            self.cfg["playback_source"] = None

        fallback = self._resolve_initial_source()
        if fallback:
            self._load_source(*fallback)
        else:
            self._load_token += 1
            self.images, self.index = [], -1
            self._active_kind, self._active_id = "folder", None
            self._refresh_source_menu()
            self.preview.configure(image=None, text="Add a folder to begin")
            self.meta.configure(text="")
            self._flush_save()

    # ---------------- Collections (saved tag filters) ----------------

    def _open_collection_editor(self, collection: Optional[dict] = None) -> None:
        win = ctk.CTkToplevel(self)
        win.title("New Collection" if collection is None else f"Edit Collection — {collection['name']}")
        win.geometry("360x240")
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text="Collection name").pack(padx=16, pady=(16, 4), anchor="w")
        name_var = ctk.StringVar(value=collection["name"] if collection else "")
        ctk.CTkEntry(win, textvariable=name_var).pack(padx=16, fill="x")

        ctk.CTkLabel(win, text="Match images tagged with any of").pack(
            padx=16, pady=(16, 4), anchor="w")
        tags_var = ctk.StringVar(
            value=", ".join(collection["tags_any"]) if collection else ""
        )
        ctk.CTkEntry(win, textvariable=tags_var, placeholder_text="nature, minimal").pack(
            padx=16, fill="x")
        ctk.CTkLabel(
            win, text="Tag images from the main window's Tags field first.",
            text_color="gray60", font=ctk.CTkFont(size=11), wraplength=320,
        ).pack(padx=16, pady=(6, 0), anchor="w")

        def do_save() -> None:
            name = name_var.get().strip()
            tags_any = dedupe_preserve_order([t.strip() for t in tags_var.get().split(",") if t.strip()])
            if not name or not tags_any:
                messagebox.showerror(
                    APP_NAME, "Collection needs a name and at least one tag.", parent=win
                )
                return
            if collection is None:
                created = {"id": new_id(), "name": name, "tags_any": tags_any}
                self.cfg["collections"].append(created)
                self._load_source("collection", created["id"])
            else:
                collection["name"] = name
                collection["tags_any"] = tags_any
                if self._active_kind == "collection" and self._active_id == collection["id"]:
                    self._load_source("collection", collection["id"])
                else:
                    self._refresh_source_menu()
            self._flush_save()
            win.destroy()

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(padx=16, pady=12, fill="x")
        ctk.CTkButton(btns, text="Save", command=do_save).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(btns, text="Cancel", fg_color="gray30", hover_color="gray25",
                      command=win.destroy).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _edit_active_collection(self) -> None:
        if self._active_kind != "collection":
            self._set_status("Select a collection to edit.")
            return
        collection = find_collection(self.cfg, self._active_id)
        if collection is not None:
            self._open_collection_editor(collection)

    def _delete_active_collection(self) -> None:
        if self._active_kind != "collection":
            self._set_status("Select a collection to delete.")
            return
        collection = find_collection(self.cfg, self._active_id)
        if collection is None:
            return
        if not messagebox.askyesno(
            APP_NAME,
            f"Delete collection '{collection['name']}'?\n\n(No image files or tags are deleted.)",
        ):
            return
        self._stop_slideshow()
        self.cfg["collections"] = [
            c for c in self.cfg["collections"] if c["id"] != collection["id"]
        ]
        if self.cfg.get("playback_source") and self.cfg["playback_source"]["id"] == collection["id"]:
            self.cfg["playback_source"] = None

        fallback = self._resolve_initial_source()
        if fallback:
            self._load_source(*fallback)
        else:
            self._load_token += 1
            self.images, self.index = [], -1
            self._active_kind, self._active_id = "folder", None
            self._refresh_source_menu()
            self.preview.configure(image=None, text="Add a folder to begin")
            self.meta.configure(text="")
            self._flush_save()

    # ---------------- Favourites / hidden (non-destructive curation) ----------------

    def _toggle_favourite(self) -> None:
        if not (0 <= self.index < len(self.images)):
            return
        path = self.images[self.index]
        is_fav = path in self.cfg.get("favourites", [])
        set_membership(self.cfg, "favourites", path, not is_fav)
        self._update_favourite_button()
        self._schedule_save()

    def _update_favourite_button(self) -> None:
        favourited = (
            0 <= self.index < len(self.images)
            and self.images[self.index] in self.cfg.get("favourites", [])
        )
        if favourited:
            self.fav_btn.configure(text="♥ Favourited", fg_color="#b71c1c", hover_color="#951616")
        else:
            self.fav_btn.configure(text="♡ Favourite", fg_color="gray30", hover_color="gray25")

    def _update_hidden_count_label(self) -> None:
        self.hidden_btn.configure(text=f"Hidden ({len(self.cfg.get('hidden', []))})")

    def _update_tags_field(self) -> None:
        if 0 <= self.index < len(self.images):
            self.tags_var.set(", ".join(get_tags(self.cfg, self.images[self.index])))
        else:
            self.tags_var.set("")

    def _on_tags_apply(self) -> None:
        if not (0 <= self.index < len(self.images)):
            return
        path = self.images[self.index]
        tags = [t.strip() for t in self.tags_var.get().split(",")]
        set_tags(self.cfg, path, tags)
        self.tags_var.set(", ".join(get_tags(self.cfg, path)))
        self._flush_save()
        self._set_status("Tags updated.")

    def _hide_current(self) -> None:
        if not (0 <= self.index < len(self.images)):
            return
        path = self.images[self.index]
        set_membership(self.cfg, "hidden", path, True)
        name = Path(path).name
        self.images = (
            resolve_source_images(self.cfg, self._active_kind, self._active_id)
            if self._active_id else []
        )
        self._load_token += 1
        if self.images:
            self.index = min(self.index, len(self.images) - 1)
            self._show_current()
        else:
            self.index = -1
            self.preview.configure(image=None, text="No images left in this source")
            self.meta.configure(text="")
            self._update_favourite_button()
            self._update_tags_field()
        self._set_status(f"Hidden {name}. Use \"Hidden\" to restore it.")
        self._update_hidden_count_label()
        self._flush_save()

    def _open_hidden_manager(self) -> None:
        win = ctk.CTkToplevel(self)
        win.title("Hidden Images")
        win.geometry("420x420")
        win.transient(self)
        win.grab_set()
        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(padx=16, pady=16, fill="both", expand=True)

        def rebuild() -> None:
            for w in scroll.winfo_children():
                w.destroy()
            hidden = self.cfg.get("hidden", [])
            if not hidden:
                ctk.CTkLabel(scroll, text="No hidden images.", text_color="gray60").pack(pady=8)
                return
            for path in hidden:
                item = ctk.CTkFrame(scroll, fg_color="transparent")
                item.pack(fill="x", pady=2)
                ctk.CTkLabel(item, text=Path(path).name, anchor="w").pack(
                    side="left", fill="x", expand=True)

                def unhide(p=path) -> None:
                    set_membership(self.cfg, "hidden", p, False)
                    if self._active_id is not None:
                        self.images = resolve_source_images(
                            self.cfg, self._active_kind, self._active_id
                        )
                    self._flush_save()
                    self._update_hidden_count_label()
                    rebuild()

                ctk.CTkButton(item, text="Unhide", width=70, command=unhide).pack(side="right")

        rebuild()

    # ---------------- Drive reconnect watcher ----------------

    def _start_reconnect_watcher(self) -> None:
        self._reconnect_job = self.after(RECONNECT_POLL_MS, self._reconnect_tick)

    def _reconnect_tick(self) -> None:
        if self._closing:
            return
        had_no_images = not self.images
        self._refresh_source_menu()  # refreshes offline badges without user action
        if had_no_images and self._active_id is not None:
            images = resolve_source_images(self.cfg, self._active_kind, self._active_id)
            if images:
                self.images = images
                self.index = 0
                self._load_token += 1
                self._set_status("Source reconnected — resuming.")
                self._show_current()
        self._reconnect_job = self.after(RECONNECT_POLL_MS, self._reconnect_tick)

    # ---------------- Preview sizing ----------------

    def _on_preview_configure(self, event=None) -> None:
        """Recompute 16:9 preview box from available widget size."""
        try:
            w = max(self.preview.winfo_width(), 1)
            h = max(self.preview.winfo_height(), 1)
        except Exception:
            return
        # Leave a little margin; fit largest 16:9 rectangle inside the label.
        if w / h > ASPECT_RATIO:
            box_h = h
            box_w = int(h * ASPECT_RATIO)
        else:
            box_w = w
            box_h = int(w / ASPECT_RATIO)
        box_w = max(box_w, 160)
        box_h = max(box_h, 90)
        new_size = (box_w, box_h)
        old_w, old_h = self._preview_size
        if abs(new_size[0] - old_w) > 8 or abs(new_size[1] - old_h) > 8:
            self._preview_size = new_size
            # Re-render current preview at new size if we have an image.
            if 0 <= self.index < len(self.images):
                self._show_current()

    # ---------------- Preview & navigation ----------------

    def _show_current(self) -> None:
        if self._closing or not (0 <= self.index < len(self.images)):
            return
        path = self.images[self.index]
        self._load_token += 1
        token = self._load_token
        max_w, max_h = self._preview_size

        def work() -> None:
            try:
                img, width, height = _load_preview_image(path, max_w, max_h)
                size_bytes = os.path.getsize(path)
            except Exception as exc:
                log.warning("Preview load failed for %s: %s", path, exc)
                # Python clears `exc` when the except block exits, and this
                # lambda runs later via `after()` — bind it as a default
                # argument now or the callback raises NameError instead of
                # showing the intended error.
                self.after(0, lambda exc=exc: self._on_preview_error(token, path, exc))
                return
            self.after(
                0,
                lambda: self._on_preview_ready(token, path, img, width, height, size_bytes),
            )

        self._executor.submit(work)
        # Debounced save of current_image — do NOT write on every show synchronously.
        self._schedule_save()

    def _on_preview_error(self, token: int, path: str, exc: BaseException) -> None:
        if token != self._load_token or self._closing:
            return
        self.preview.configure(image=None, text=f"Cannot open image\n{Path(path).name}")
        self.meta.configure(text=str(exc))
        self._refresh_source_menu()  # a missing file often means a drive went offline

    def _on_preview_ready(
        self,
        token: int,
        path: str,
        img: Image.Image,
        width: int,
        height: int,
        size_bytes: int,
    ) -> None:
        if token != self._load_token or self._closing:
            return
        try:
            self._preview_ref = ctk.CTkImage(
                light_image=img, dark_image=img, size=img.size
            )
            self.preview.configure(image=self._preview_ref, text="")
            size = human_size(size_bytes)
            self.meta.configure(
                text=f"{Path(path).name}    •    {width} × {height}    •    {size}    "
                     f"•    {self.index + 1} of {len(self.images)}"
            )
            self._update_favourite_button()
            self._update_hidden_count_label()
            self._update_tags_field()
        except Exception as exc:
            log.warning("Preview apply failed: %s", exc)

    def _reset_slideshow_timer_if_running(self) -> None:
        """On manual navigation, restart the slideshow countdown if active."""
        if self._slideshow_job is not None:
            try:
                self.after_cancel(self._slideshow_job)
            except Exception:
                pass
            self._slideshow_job = None
            self._schedule_next()

    def _step(self, delta: int) -> None:
        if not self.images:
            return
        self.index = (self.index + delta) % len(self.images)
        self._show_current()
        self._reset_slideshow_timer_if_running()

    def _prev(self) -> None:
        self._step(-1)

    def _next(self) -> None:
        self._step(1)

    def _advance_shuffle(self) -> None:
        """Advance using the Fisher–Yates deck (used by slideshow tick)."""
        if not self.images:
            return
        if len(self.images) == 1:
            self.index = 0
            self._show_current()
            return
        if not self._shuffle_order or self._shuffle_cursor >= len(self._shuffle_order):
            self._shuffle_order = build_shuffle_deck(len(self.images), self.index)
            self._shuffle_cursor = 0
        if self._shuffle_order:
            self.index = self._shuffle_order[self._shuffle_cursor]
            self._shuffle_cursor += 1
            self._show_current()

    def _random(self) -> None:
        if not self.images:
            return
        self._advance_shuffle()
        self._reset_slideshow_timer_if_running()

    # ---------------- Wallpaper ----------------

    def _on_style_changed(self, _value: str) -> None:
        self._flush_save()
        if 0 <= self.index < len(self.images):
            try:
                set_windows_wallpaper(self.images[self.index], self.style_var.get())
                self._set_status(f"Style applied: {self.style_var.get()}")
            except Exception as exc:
                # On non-Windows, just save the preference.
                log.info("Style change wallpaper reapply skipped: %s", exc)
                self._set_status(f"Style saved: {self.style_var.get()}")

    def _on_shuffle_changed(self) -> None:
        self._shuffle_order = []
        self._shuffle_cursor = 0
        self._save()

    def _on_power_settings_changed(self) -> None:
        self.cfg["power"] = {
            "pause_on_battery_saver": bool(self.battery_pause_var.get()),
            "pause_on_fullscreen": bool(self.fullscreen_pause_var.get()),
        }
        self._schedule_save()

    def _on_schedule_mode_changed(self, value: str) -> None:
        self.cfg["schedule"]["mode"] = "daily" if value == "Daily times" else "interval"
        self._flush_save()
        if self._slideshow_running:
            self._stop_slideshow(update_status=False)
            self._start_slideshow()

    def _on_daily_times_apply(self) -> None:
        raw_times = [t.strip() for t in self.daily_times_var.get().split(",") if t.strip()]
        invalid = [t for t in raw_times if not is_valid_time_string(t)]
        if invalid:
            messagebox.showerror(
                APP_NAME, f"Invalid time(s): {', '.join(invalid)}\nUse 24-hour HH:MM, e.g. 08:00."
            )
            return
        self.cfg["schedule"]["daily_times"] = raw_times
        self.daily_times_var.set(", ".join(raw_times))
        self._flush_save()
        self._set_status(f"Daily schedule times updated ({len(raw_times)}).")
        if self._slideshow_running and self.cfg["schedule"]["mode"] == "daily":
            self._stop_slideshow(update_status=False)
            self._start_slideshow()

    def _set_wallpaper(self, silent: bool = False) -> None:
        if not (0 <= self.index < len(self.images)):
            self._set_status("Nothing selected.")
            return
        path = self.images[self.index]
        try:
            set_windows_wallpaper(path, self.style_var.get())
            self._set_status(f"Wallpaper set: {Path(path).name}")
        except Exception as exc:
            if silent:
                # Unattended slideshow: never block on a modal dialog — most
                # often this just means a drive went offline mid-run.
                log.warning("Slideshow could not set wallpaper for %s: %s", path, exc)
                self._set_status(f"Skipped (unavailable): {Path(path).name}")
                self._refresh_source_menu()
            else:
                messagebox.showerror(APP_NAME, f"Could not set wallpaper:\n{exc}")

    # ---------------- Slideshow ----------------

    def _interval_display_text(self) -> str:
        key = self.interval_var.get()
        if key == CUSTOM_INTERVAL_LABEL:
            seconds = resolve_interval_seconds(key, self.cfg.get("interval_custom_seconds"))
            return f"{seconds}s (custom)"
        return key

    def _on_interval_changed(self, value: str) -> None:
        if value == CUSTOM_INTERVAL_LABEL:
            current = self.cfg.get("interval_custom_seconds") or 60
            seconds = simpledialog.askinteger(
                APP_NAME,
                "Custom slideshow interval, in seconds:",
                initialvalue=current,
                minvalue=MIN_CUSTOM_INTERVAL_SECONDS,
                maxvalue=MAX_CUSTOM_INTERVAL_SECONDS,
                parent=self,
            )
            if seconds is None:
                # Cancelled — revert the dropdown to whatever was selected before.
                self.interval_var.set(self.cfg.get("interval", DEFAULT_CONFIG["interval"]))
                return
            self.cfg["interval_custom_seconds"] = seconds
        self._flush_save()
        if self._slideshow_running:
            self._stop_slideshow(update_status=False)
            self._start_slideshow()

    def _toggle_slideshow(self) -> None:
        if self._slideshow_running:
            self._stop_slideshow()
        else:
            self._start_slideshow()

    def _auto_pause_status_text(self) -> str:
        labels = {
            "battery_saver": "Battery Saver is on",
            "fullscreen": "a fullscreen app is active",
        }
        reasons = ", ".join(labels[r] for r in sorted(self._auto_pause_reasons) if r in labels)
        return f"Slideshow paused — {reasons}."

    def _start_slideshow(self) -> None:
        if not self.images:
            self._set_status("Add a folder with images first.")
            return
        self._slideshow_running = True
        self.slide_btn.configure(text="Stop Slideshow", fg_color="#b71c1c", hover_color="#951616")
        if self._auto_pause_reasons:
            self._set_status(self._auto_pause_status_text())
            return
        self._set_status(f"Slideshow running — every {self._interval_display_text()}.")
        self._set_wallpaper(silent=True)
        self._schedule_next()

    def _schedule_next(self) -> None:
        if not self.images:
            self._stop_slideshow()
            return
        if self.cfg["schedule"]["mode"] == "daily":
            trigger = next_daily_trigger(datetime.now(), self.cfg["schedule"]["daily_times"])
            seconds = (
                max(1, int((trigger - datetime.now()).total_seconds()))
                if trigger is not None
                # No valid daily times configured — fall back to the fixed
                # interval so the slideshow doesn't silently stall forever.
                else resolve_interval_seconds(
                    self.interval_var.get(), self.cfg.get("interval_custom_seconds")
                )
            )
        else:
            seconds = resolve_interval_seconds(
                self.interval_var.get(), self.cfg.get("interval_custom_seconds")
            )
        self._slideshow_job = self.after(seconds * 1000, self._slideshow_tick)

    def _slideshow_tick(self) -> None:
        self._slideshow_job = None
        if not self.images:
            self._stop_slideshow()
            return
        # Advance without treating this as manual nav (avoids timer reset races).
        if self.shuffle_var.get():
            self._advance_shuffle()
        else:
            self.index = (self.index + 1) % len(self.images)
            self._show_current()
        self._set_wallpaper(silent=True)
        if self.images:
            self._schedule_next()
        else:
            self._stop_slideshow()

    def _stop_slideshow(self, update_status: bool = True) -> None:
        self._slideshow_running = False
        if self._slideshow_job is not None:
            try:
                self.after_cancel(self._slideshow_job)
            except Exception:
                pass
            self._slideshow_job = None
        try:
            self.slide_btn.configure(
                text="Start Slideshow", fg_color="#2e7d32", hover_color="#27682a"
            )
        except Exception:
            pass
        if update_status:
            self._set_status("Slideshow stopped.")

    # ---------------- Power & fullscreen auto-pause ----------------

    def _start_power_monitor(self) -> None:
        self._power_job = self.after(POWER_POLL_MS, self._power_monitor_tick)

    def _power_monitor_tick(self) -> None:
        if self._closing:
            return
        reasons: set[str] = set()
        if self.cfg["power"]["pause_on_battery_saver"] and is_battery_saver_active():
            reasons.add("battery_saver")
        if self.cfg["power"]["pause_on_fullscreen"] and is_fullscreen_active():
            reasons.add("fullscreen")
        was_paused = bool(self._auto_pause_reasons)
        if reasons != self._auto_pause_reasons:
            self._auto_pause_reasons = reasons
            if self._slideshow_running:
                if reasons and not was_paused:
                    if self._slideshow_job is not None:
                        try:
                            self.after_cancel(self._slideshow_job)
                        except Exception:
                            pass
                        self._slideshow_job = None
                    self._set_status(self._auto_pause_status_text())
                elif not reasons and was_paused:
                    self._set_status(f"Slideshow running — every {self._interval_display_text()}.")
                    self._schedule_next()
        self._power_job = self.after(POWER_POLL_MS, self._power_monitor_tick)

    # ---------------- Startup (Run key) ----------------

    def _sync_startup_state(self) -> None:
        """Reflect the actual registry state in the switch, and reconcile config."""
        actual = is_startup_enabled()
        self.startup_var.set(actual)
        tray_cfg = self.cfg.get("tray", {})
        if tray_cfg.get("run_at_startup") != actual:
            self.cfg["tray"] = {**tray_cfg, "run_at_startup": actual}
            self._schedule_save()

    def _on_startup_toggle(self) -> None:
        enabled = bool(self.startup_var.get())
        try:
            set_startup_enabled(enabled)
        except Exception as exc:
            log.warning("Could not update startup entry: %s", exc)
            self.startup_var.set(not enabled)
            messagebox.showerror(APP_NAME, f"Could not update Windows startup setting:\n{exc}")
            return
        self.cfg["tray"] = {**self.cfg.get("tray", {}), "run_at_startup": enabled}
        self._schedule_save()
        self._set_status("Start with Windows: " + ("on" if enabled else "off"))

    # ---------------- System tray ----------------

    def _tray_available(self) -> bool:
        return pystray is not None and sys.platform == "win32"

    def _init_tray(self) -> None:
        if not self._tray_available():
            return
        if not self.cfg.get("tray", {}).get("enabled", True):
            return
        try:
            self._start_tray_icon()
        except Exception as exc:
            log.warning("Tray icon unavailable, falling back to normal close: %s", exc)
            self.tray_icon = None

    def _tray_menu_items(self) -> tuple:
        if 0 <= self.index < len(self.images):
            current_name = f"Current: {Path(self.images[self.index]).name}"
        else:
            current_name = "Current: (none)"
        slideshow_running = self._slideshow_running
        return (
            pystray.MenuItem(current_name, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Desktop Vista", self._on_tray_restore, default=True),
            pystray.MenuItem("Next Wallpaper", self._on_tray_next),
            pystray.MenuItem("Previous Wallpaper", self._on_tray_prev),
            pystray.MenuItem(
                "Pause Slideshow" if slideshow_running else "Resume Slideshow",
                self._on_tray_toggle_slideshow,
            ),
            pystray.MenuItem("Reveal in Explorer", self._on_tray_reveal),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._on_tray_exit),
        )

    def _start_tray_icon(self) -> None:
        if self.tray_icon is not None:
            return
        image = load_brand_icon()
        menu = pystray.Menu(self._tray_menu_items)
        self.tray_icon = pystray.Icon(APP_NAME, image, APP_NAME, menu)
        self._tray_ready = threading.Event()
        self._tray_failed = False

        def _run() -> None:
            def _on_setup(icon) -> None:
                icon.visible = True
                self._tray_ready.set()

            try:
                self.tray_icon.run(setup=_on_setup)
            except Exception as exc:
                log.warning("Tray icon thread failed: %s", exc)
                self._tray_failed = True
                self._tray_ready.set()

        self._tray_thread = threading.Thread(target=_run, name="dv-tray", daemon=True)
        self._tray_thread.start()

    def _tray_is_ready(self, timeout: float = 2.0) -> bool:
        """Block briefly for the tray thread to signal success/failure.

        Storing a non-None Icon the instant it's constructed (before its
        background thread actually starts serving) let a startup failure
        leave --minimized hiding the only window with no working way to
        restore it. Waiting on an explicit readiness event closes that gap.
        """
        if self.tray_icon is None or self._tray_ready is None:
            return False
        self._tray_ready.wait(timeout)
        return self._tray_ready.is_set() and not self._tray_failed

    def _stop_tray_icon(self) -> None:
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        self._tray_ready = None
        self._tray_failed = False

    # pystray invokes these on its own thread — always marshal back onto Tk's.
    def _on_tray_restore(self, _icon=None, _item=None) -> None:
        self.after(0, self._tray_restore)

    def _tray_restore(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_tray_next(self, _icon=None, _item=None) -> None:
        self.after(0, self._tray_navigate_and_apply, 1)

    def _on_tray_prev(self, _icon=None, _item=None) -> None:
        self.after(0, self._tray_navigate_and_apply, -1)

    def _tray_navigate_and_apply(self, delta: int) -> None:
        """Tray "Next/Previous Wallpaper" must change the desktop, not just
        the in-window preview — the main window's arrow buttons keep the
        preview-only behaviour via `_step`/`_prev`/`_next`."""
        self._step(delta)
        self._set_wallpaper(silent=True)

    def _on_tray_toggle_slideshow(self, _icon=None, _item=None) -> None:
        self.after(0, self._toggle_slideshow)

    def _on_tray_reveal(self, _icon=None, _item=None) -> None:
        self.after(0, self._reveal_current_in_explorer)

    def _reveal_current_in_explorer(self) -> None:
        if not (0 <= self.index < len(self.images)):
            self._set_status("Nothing to reveal.")
            return
        path = self.images[self.index]
        try:
            # Windows paths cannot contain '"', so this cannot break out of
            # the /select argument; no shell is involved (shell=False).
            subprocess.Popen(f'explorer /select,"{path}"')
        except OSError as exc:
            log.warning("Reveal in Explorer failed: %s", exc)
            self._set_status("Could not open Explorer.")

    def _on_tray_exit(self, _icon=None, _item=None) -> None:
        self.after(0, self._on_close)

    # ---------------- Close ----------------

    def _cancel_after_jobs(self) -> None:
        for attr in ("_slideshow_job", "_save_job", "_reconnect_job", "_power_job"):
            job = getattr(self, attr, None)
            if job is not None:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
                setattr(self, attr, None)

    def _on_close_request(self) -> None:
        """Handle the window's close button: hide to tray if it's running."""
        if self.tray_icon is not None and self.cfg.get("tray", {}).get("close_to_tray", True):
            self._flush_save()
            self.withdraw()
        else:
            self._on_close()

    def _on_close(self) -> None:
        self._closing = True
        self._load_token += 1  # invalidate in-flight preview loads
        self._cancel_after_jobs()
        self._write_config()
        self._stop_tray_icon()
        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            # Python < 3.9 cancel_futures not available
            self._executor.shutdown(wait=False)
        self.destroy()


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Desktop Vista is designed for Windows.")
    start_minimized = "--minimized" in sys.argv[1:]
    DesktopVista(start_minimized=start_minimized).mainloop()
