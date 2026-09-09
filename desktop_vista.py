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
Version 1.7  (September 2026)

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

v1.5.1 — v2.0 groundwork, not v2.0 itself:
    - windows_wallpaper_com.py: a real IDesktopWallpaper COM backend
      (comtypes), imported lazily and only ever touched when
      config.wallpaper_target is switched to "com" (default stays "spi",
      the existing global SystemParametersInfoW path — zero behaviour
      change unless a user opts in)
    - UI: "Per-monitor engine (COM)" toggle + a target-monitor picker;
      "Set as Wallpaper" applies to the chosen display via COM when
      enabled, otherwise the unchanged global path
    - This is a manual per-monitor APPLY, not independent per-monitor
      slideshows — there is one shared index/navigation/slideshow state
      still. Verified on the development machine (single display): COM
      object creation, monitor enumeration, and SetWallpaper/SetPosition
      for both the all-displays and the one real monitor's specific
      target all succeed and visibly change the desktop. NOT verified
      anywhere: two different images actually showing independently on
      two different physical displays — that needs real multi-monitor
      hardware. Treat the per-monitor claim as unconfirmed until checked.

Still ahead for the full v2.0 milestone: independent per-monitor
slideshow/navigation state, the span crop assistant, wiring tags into the
*applied* wallpaper (not just the UI), and a go/no-go decision on desktop
crossfade — see ROADMAP.md.

New in v1.6 "Scriptable companion" (notes/notes_005.txt) — last release
before the multi-monitor rewrite; nothing here requires a second display:
    - Fixed a real v1.5 defect: a saved collection playback_source was
      silently dropped on restart (_validate_config's kind whitelist and
      _resolve_initial_source had no "collection" branch)
    - Playback history ring (100 applied wallpapers, playback_state.json)
      with Undo; tray "Previous" now walks this history instead of
      decrementing the raw index, since shuffle order isn't linear
    - 1 Hz scheduler heartbeat replaces one long after(seconds * 1000):
      polls a due-time instead of arming a single-shot timer, so a
      sleep/hibernate gap finds "due" true at most once on resume rather
      than firing a catch-up burst
    - Solar dawn/day/dusk/night wired into the live slideshow (schedule.py):
      advances at real sun-position boundaries when a location is set,
      biases the next pick toward phase-tagged images when the library has
      any, and never stalls a library with no solar tags
    - Single-instance guard (CreateMutexW) — a second launch forwards to
      the running instance instead of opening a duplicate window
    - Named-pipe CLI IPC (ipc.py): --next/--prev/--pause/--resume/--toggle/
      --status/--set/--favourite/--hide/--undo control the running
      instance from a script or Task Scheduler; pipe is owner-only (SDDL),
      not world-accessible
    - Global hotkeys (hotkeys.py, RegisterHotKey on a dedicated thread):
      Win+Alt+N/P/L/H/Z/S by default; a bind conflict with another running
      application is logged and shown, never silently retried
    - Preview decode cancellation: navigating rapidly cancels the previous
      still-queued decode instead of letting a burst of stale work run to
      completion; the 15s reconnect poll now probes folder reachability
      off the Tk thread so an unreachable NAS/UNC path can no longer
      freeze the window

v1.6.1 — UI hardening addendum (notes/notes_006.txt Phase A defects):
    - Keyboard shortcuts (Space/Enter/arrows/p/r/f/h/Esc) no longer leak
      into text-entry widgets: typing "forest" into the Tags field used to
      also trigger Favourite (on 'f') and Random (on 'r') because CTkEntry
      wraps a real Tk Entry and toplevel bindings still see those keys.
      See _shortcut/_focus_is_text_entry.
    - Fit Style is a staged preference again, not an apply command:
      _on_style_changed used to call set_windows_wallpaper directly and
      unconditionally — always through the legacy global SPI path, even
      with the experimental per-monitor COM engine and a specific target
      monitor selected. The new style now takes effect on the next
      explicit apply, same as everywhere else style_var is read.

New in v1.7 (notes/notes_006.txt phases B-D — UI/interaction rewrite):
    - Four task pages (Library / Playback / Displays / Settings) replace
      the single 11-section sidebar stack, via a small vertical nav rail;
      pages are built once and shown/hidden with grid()/grid_remove(),
      never rebuilt, so widget state and scroll position survive a switch
    - The three stacked button rows under the preview are gone. A floating
      HoverHUD (new ui_components.py) — Previous/Random/Next, Favourite/
      Hide/Tags/More — reveals on stage hover/focus/F6 and hides after
      ~2.5s idle; a permanent stage footer (filename/status left, one
      "Apply to <target>" button right) is the single, stable primary
      action, outside any scroll region
    - Tag editing moved from a raw comma-separated Entry to a chip-based
      TagSelector drawer (exact-string, case-sensitive — unchanged
      semantics) with autocomplete; the stage shows a subdued read-only
      summary badge. Editing captures the image path when the drawer
      opens, so navigating away mid-edit can't redirect the write onto a
      different image
    - A bounded ToastManager posts transient confirmations (wallpaper
      applied, favourited, hidden) alongside the existing persistent
      status line, which stays authoritative — this is additive, not a
      replacement
    - Appearance is switchable (System/Light/Dark, Settings page) instead
      of hard-coded dark; the raw Tk monitor-topology Canvas is restyled
      to match since CTk's colour tuples don't reach native Canvas
      primitives
    - Keyboard remap (documented, one-time in-app notice on first launch
      after update): Space now starts/stops the slideshow (was Next);
      Esc now closes the active panel — tag drawer, shortcut help,
      inspection mode — instead of stopping the slideshow (the Playback
      page's Start/Stop button is the always-visible non-keyboard way to
      stop it). New: F6 reveals the HUD, F11 toggles a borderless fit-to-
      screen inspection preview (no zoom/pan yet), ? shows a shortcut
      reference, Ctrl+Z undoes the last applied wallpaper
    - Hidden Items manager now shows each item's parent folder (with an
      offline badge) alongside the filename, so two same-named files on
      different drives are distinguishable, plus a search filter
    - Presentation-only preferences live under a new namespaced cfg["ui"]
      key (selected_page, appearance, hud_always_visible, reduced_motion,
      seen_shortcut_notice_v2) — never engine state, independently
      validated and defaulted like every other config section

    Deliberately not done this release (see ROADMAP.md): the playlist/
    collection editors keep their existing fixed-geometry dialogs rather
    than the proposed draft-state/inline-validation redesign; the Win32
    topology strip and the COM monitor picker are still two independently
    enumerated, unreconciled identity spaces, so the topology view stays
    read-only rather than becoming a clickable per-display target (that
    needs notes_005's fingerprinting scheme — v2.0 work); no accent-colour
    sync, ambient glow, or drag-to-assign (v2.1-scope polish); no
    Narrator/high-contrast/multi-DPI verification performed — this needs
    real assistive-technology and multi-monitor hardware, which notes_006
    itself flags as unverified in its own review.
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
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

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

try:
    import windows_wallpaper_com
except ImportError:
    # Missing comtypes, non-Windows, or (Desktop Vista's own guard) any
    # platform windows_wallpaper_com itself declines to load on. The
    # experimental per-monitor toggle stays disabled in the UI when this
    # is None; the default "spi" wallpaper_target never touches it.
    windows_wallpaper_com = None  # type: ignore[assignment]

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps
from tkinter import Canvas, Menu, filedialog, messagebox, simpledialog

import hotkeys
import ipc
import schedule
import ui_components

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
APP_VERSION = "1.8"
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
PLAYBACK_STATE_PATH = APP_DIR / "playback_state.json"
BRAND_ICON_PATH = RESOURCE_DIR / "icon" / "desktop_vista.ico"
LICENSE_PATH = RESOURCE_DIR / "LICENSE"

# Baked at import time rather than read from LICENSE at paint time — a
# frozen build's RESOURCE_DIR lookup is exactly what --selftest exists to
# verify, not something the Settings page should depend on just to show a
# copyright line (notes_007 §1.5). The "Licence notice" button tries the
# real LICENSE file first and falls back to this short paragraph.
ABOUT_COPY: tuple[str, ...] = (
    f"{APP_NAME} {APP_VERSION}" + ("  (frozen)" if FROZEN else ""),
    "Copyright (c) 2026-present Mark Hawksworth",
    "All rights reserved.",
    "https://github.com/hawkers63/",
)
LICENCE_NOTICE_FALLBACK = (
    "Copyright (c) 2026-present Mark Hawksworth (https://github.com/hawkers63/). "
    "All Rights Reserved.\n\n"
    "This software and all associated source code, documentation, configuration "
    "templates, notes, and other materials in this repository (the \"Software\") "
    "are the exclusive proprietary property of Mark Hawksworth "
    "(https://github.com/hawkers63/).\n\n"
    "PERMISSION IS NOT GRANTED for any person or entity to copy, reproduce, "
    "redistribute, publish, modify, reverse-engineer, decompile, disassemble, "
    "create derivative works from, sublicense, sell, or commercially exploit "
    "the Software, in whole or in part, without prior written consent from "
    "the copyright holder."
)

HISTORY_MAX = 100  # ring of successfully-applied wallpapers, for tray Previous/Undo

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

SCHEDULE_MODE_LABELS = {
    "interval": "Fixed interval",
    "daily": "Daily times",
    "solar": "Solar (dawn/day/dusk/night)",
}
SCHEDULE_LABEL_TO_MODE = {label: mode for mode, label in SCHEDULE_MODE_LABELS.items()}

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
    # v2.0 experimental — "spi" (default, global SystemParametersInfoW) never
    # touches windows_wallpaper_com; "com" opts into the per-monitor engine.
    "wallpaper_target": "spi",
    # v1.6 — global hotkeys (RegisterHotKey), default set from notes_005 §2.3.1.
    # Bindings are "Mod+Mod+Key" text so a future rebind UI needs no schema
    # change; each is independently re-validated with hotkeys.parse_binding.
    "hotkeys": {
        "enabled": True,
        "next": "Win+Alt+N",
        "prev": "Win+Alt+P",
        # "F" (notes_005's suggested mnemonic) collides with an existing
        # system-wide binding on Mark's dev machine (likely a GPU driver
        # overlay) — verified live via RegisterHotKey; "L" (for "Like") is
        # free there and just as mnemonic. Still independently rebindable
        # per-action in config.json if it ever collides with something else.
        "favourite": "Win+Alt+L",
        "hide": "Win+Alt+H",
        "undo": "Win+Alt+Z",
        "toggle": "Win+Alt+S",
    },
    # v1.7 — presentation-only preferences (notes_006 §5): never store
    # temporary focus, animation progress or widget objects here, only
    # durable choices. Namespaced so it can grow without touching the
    # engine keys above; validated the same as every other section.
    "ui": {
        "selected_page": "library",  # "library"|"playback"|"displays"|"settings"
        "appearance": "dark",  # "system"|"light"|"dark" — matches the pre-v1.7 forced-dark default
        "hud_always_visible": False,
        "reduced_motion": False,
        "seen_shortcut_notice_v2": False,
    },
}

HOTKEY_ACTIONS = ("next", "prev", "favourite", "hide", "undo", "toggle")
# Stable per-action ids for RegisterHotKey/WM_HOTKEY (arbitrary but fixed).
HOTKEY_ACTION_IDS = {action: i + 1 for i, action in enumerate(HOTKEY_ACTIONS)}

UI_PAGES = ("library", "playback", "displays", "settings")
UI_PAGE_LABELS = {"library": "Library", "playback": "Playback", "displays": "Displays", "settings": "Settings"}
UI_APPEARANCE_VALUES = ("system", "light", "dark")
UI_APPEARANCE_LABELS = {"system": "System", "light": "Light", "dark": "Dark"}
UI_APPEARANCE_LABEL_TO_VALUE = {label: value for value, label in UI_APPEARANCE_LABELS.items()}

STARTUP_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE_NAME = "DesktopVista"

RECONNECT_POLL_MS = 15_000
POWER_POLL_MS = 5_000
SCHEDULER_TICK_MS = 1_000
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


def folder_display_label(folder: str, online_cache: Optional[dict[str, bool]] = None) -> str:
    """Decorate *folder* with an offline badge when its drive is unreachable.

    *online_cache*, when given, is consulted instead of probing the
    filesystem directly — an unreachable NAS/UNC path can make is_folder_online
    block for the OS's network timeout (tens of seconds), which must never
    happen on the Tk thread. Callers on a recurring/automatic path (the
    reconnect poll) pass the cache the background probe last populated;
    one-off, user-initiated dialogs (playlist editor, etc.) still probe
    directly since a single brief check there is expected UI behaviour,
    same as a native file picker validating a path.
    """
    if online_cache is not None:
        online = online_cache.get(folder, True)
    else:
        online = is_folder_online(folder)
    return folder if online else f"{folder}{OFFLINE_SUFFIX}"


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


def playlist_folder_status(
    playlist: dict, online_cache: Optional[dict[str, bool]] = None
) -> tuple[int, int]:
    """Return (online_count, total_count) for a playlist's member folders.
    See folder_display_label for *online_cache*."""
    folders = playlist.get("folders", [])
    if online_cache is not None:
        online = sum(1 for f in folders if online_cache.get(f, True))
    else:
        online = sum(1 for f in folders if is_folder_online(f))
    return online, len(folders)


def source_display_label(
    cfg: dict, kind: str, source_id: str, online_cache: Optional[dict[str, bool]] = None
) -> str:
    """Human-readable label for a folder, playlist, or collection source.
    See folder_display_label for *online_cache*."""
    if kind == "playlist":
        playlist = find_playlist(cfg, source_id)
        if playlist is None:
            return f"(missing playlist {source_id})"
        online, total = playlist_folder_status(playlist, online_cache)
        name = f"▶ {playlist.get('name', '(unnamed)')}"
        if total and online < total:
            return f"{name}  ({online}/{total} drives online)"
        return name
    if kind == "collection":
        collection = find_collection(cfg, source_id)
        if collection is None:
            return f"(missing collection {source_id})"
        return f"# {collection.get('name', '(unnamed)')}"
    return folder_display_label(source_id, online_cache)


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


def collection_match_count(cfg: dict, tags_any: list[str]) -> int:
    """How many images would currently match a collection with *tags_any*
    (hidden-filtered), without requiring the collection to be saved to cfg
    first — backs the collection editor's live match-count (notes_007
    §1.1 P2). Reuses resolve_source_images against a throwaway id so the
    matching semantics can never drift from the real playback path."""
    if not tags_any:
        return 0
    snapshot = dict(cfg)
    snapshot["collections"] = [{"id": "__draft__", "name": "", "tags_any": tags_any}]
    return len(resolve_source_images(snapshot, "collection", "__draft__"))


def resolve_rebuilt_index(
    images: list[str], old_index: int, preferred_path: Optional[str] = None
) -> int:
    """Resolve the index to use in a freshly-rebuilt *images* list after a
    filter-affecting change (hide/unhide, playlist/collection Save).

    *preferred_path* wins if it is still present (Unhide re-selecting the
    image it just restored). Otherwise *old_index* is clamped into range —
    this is positional, not identity-based, matching the rest of the app's
    index model (notes_007 §1.2). -1 means "nothing to show"; callers must
    not index into *images* without checking for it first.
    """
    if preferred_path is not None and preferred_path in images:
        return images.index(preferred_path)
    if images:
        return min(max(old_index, 0), len(images) - 1)
    return -1


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


def _rect_intersection_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[2], b[2])
    bottom = min(a[3], b[3])
    return max(0, right - left) * max(0, bottom - top)


def join_monitor_topology(
    gdi_monitors: list[dict], com_monitors: list[tuple[str, tuple[int, int, int, int]]]
) -> list[Optional[int]]:
    """Session-scoped join between the read-only Win32 topology
    (enumerate_monitors) and the COM device-path list
    (ComWallpaperBackend.enumerate_monitors), by maximum-area RECT
    intersection in physical pixels (notes_007 §1.3).

    Returns, for each *gdi_monitors* entry in order, the index into
    *com_monitors* it joins to, or None if the join is ambiguous (a tie —
    including two COM entries sharing one clone-mode RECT) or there is no
    overlap at all. A tie is reported unresolved rather than guessed: once
    v2.0 wires an apply target off this join, a wrong guess here means
    silently assigning wallpaper to the wrong physical display. Never
    persist the result across a session — device paths are ephemeral
    (notes_004/notes_007 house rules); re-run this every time both sides
    are freshly re-enumerated.
    """
    joins: list[Optional[int]] = []
    for gdi in gdi_monitors:
        best_area = 0
        best_index: Optional[int] = None
        tied = False
        for com_index, (_device_id, com_rect) in enumerate(com_monitors):
            area = _rect_intersection_area(gdi["rect"], com_rect)
            if area <= 0:
                continue
            if area > best_area:
                best_area = area
                best_index = com_index
                tied = False
            elif area == best_area:
                tied = True
        joins.append(None if tied else best_index)
    return joins


def is_fullscreen_active(state: Optional[int] = None) -> bool:
    """Pure predicate over a notification-state value — pass one explicitly
    in tests; real callers omit it to query the live Win32 API."""
    if state is None:
        state = query_user_notification_state()
    return state in FULLSCREEN_NOTIFICATION_STATES if state is not None else False


class _HIGHCONTRASTW(ctypes.Structure if ctypes is not None else object):
    _fields_ = (
        [
            ("cbSize", ctypes.c_uint),
            ("dwFlags", ctypes.c_uint),
            ("lpszDefaultScheme", ctypes.c_void_p),
        ]
        if ctypes is not None
        else []
    )


SPI_GETHIGHCONTRAST = 0x0042
HCF_HIGHCONTRASTON = 0x00000001


def query_high_contrast_flags() -> Optional[int]:
    """Raw SPI_GETHIGHCONTRAST dwFlags, or None if unavailable."""
    if ctypes is None or sys.platform != "win32":
        return None
    info = _HIGHCONTRASTW()
    info.cbSize = ctypes.sizeof(_HIGHCONTRASTW)
    try:
        ok = ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETHIGHCONTRAST, ctypes.sizeof(info), ctypes.byref(info), 0
        )
    except OSError:
        return None
    return info.dwFlags if ok else None


def is_high_contrast_active(flags: Optional[int] = None) -> bool:
    """Pure predicate over SPI_GETHIGHCONTRAST's dwFlags — pass one
    explicitly in tests; real callers omit it to query live. Windows'
    Ease of Access > High contrast is a separate setting from our own
    dark/light/system choice; notes_007 §1.4 says to honour it rather than
    invent a fourth appearance mode — see _apply_appearance_mode."""
    if flags is None:
        flags = query_high_contrast_flags()
    return flags is not None and bool(flags & HCF_HIGHCONTRASTON)


MDT_EFFECTIVE_DPI = 0


def enumerate_monitor_dpi() -> list[dict]:
    """Per-monitor effective DPI via Shcore's GetDpiForMonitor (Windows
    8.1+), same enumeration order as enumerate_monitors(). Returns
    [{"device": str, "dpi_x": int|None, "dpi_y": int|None}, ...], or []
    off Windows or on API failure. --selftest diagnostic only — nothing in
    the apply path reads this yet; it exists so the v2.0 mixed-DPI span
    work starts from a measurement rather than an assumption (notes_007
    §5.2)."""
    if ctypes is None or sys.platform != "win32":
        return []
    results: list[dict] = []
    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(_RECT), ctypes.c_void_p
    )

    def _callback(hmonitor, _hdc, _lprect, _data):
        info = _MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(_MONITORINFOEXW)
        device = info.szDevice if ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)) else ""
        dpi_x, dpi_y = ctypes.c_uint(0), ctypes.c_uint(0)
        try:
            hresult = ctypes.windll.shcore.GetDpiForMonitor(
                hmonitor, MDT_EFFECTIVE_DPI, ctypes.byref(dpi_x), ctypes.byref(dpi_y)
            )
        except OSError:
            hresult = -1
        if hresult == 0:  # S_OK
            results.append({"device": device, "dpi_x": dpi_x.value, "dpi_y": dpi_y.value})
        else:
            results.append({"device": device, "dpi_x": None, "dpi_y": None})
        return 1  # non-zero: keep enumerating

    try:
        ctypes.windll.user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_callback), 0)
    except OSError:
        return []
    return results


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

    # playback_source is validated further down, once collections (v1.5) has
    # also been populated — a saved collection reference needs both lists
    # to check against, not just playlists.

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
            # "solar" (v1.6): advance at dawn/day/dusk/night boundaries
            # instead of a fixed interval — see _compute_next_due/_solar_advance.
            # No dependency on solar.enabled/coordinates being valid here;
            # an unset location degrades to the fallback_times at run time
            # rather than being rejected at load time.
            "mode": mode if mode in ("interval", "daily", "solar") else "interval",
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

    playback_source = raw.get("playback_source")
    if (
        isinstance(playback_source, dict)
        and playback_source.get("kind") in ("folder", "playlist", "collection")
        and isinstance(playback_source.get("id"), str)
        and playback_source.get("id")
    ):
        kind, sid = playback_source["kind"], playback_source["id"]
        valid_ref = (
            (kind == "folder" and sid in cfg["folders"])
            or (kind == "playlist" and find_playlist(cfg, sid) is not None)
            or (kind == "collection" and find_collection(cfg, sid) is not None)
        )
        cfg["playback_source"] = {"kind": kind, "id": sid} if valid_ref else None
    else:
        cfg["playback_source"] = None

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

    # ---- v2.0 experimental (additive) ----

    wallpaper_target = raw.get("wallpaper_target", DEFAULT_CONFIG["wallpaper_target"])
    cfg["wallpaper_target"] = wallpaper_target if wallpaper_target in ("spi", "com") else "spi"

    # ---- v1.6 additions (all additive; absent/invalid -> safe defaults) ----

    hotkeys_raw = raw.get("hotkeys", DEFAULT_CONFIG["hotkeys"])
    hotkeys_defaults = DEFAULT_CONFIG["hotkeys"]
    if isinstance(hotkeys_raw, dict):
        enabled = hotkeys_raw.get("enabled")
        valid_hotkeys = {"enabled": enabled if isinstance(enabled, bool) else hotkeys_defaults["enabled"]}
        for action in HOTKEY_ACTIONS:
            binding = hotkeys_raw.get(action)
            # Each binding is independently re-validated (must still parse
            # as "Mod+Mod+Key") rather than trusted verbatim from disk —
            # falls back to the factory default per-action, not en masse.
            valid_hotkeys[action] = (
                binding
                if isinstance(binding, str) and hotkeys.parse_binding(binding) is not None
                else hotkeys_defaults[action]
            )
        cfg["hotkeys"] = valid_hotkeys
    else:
        log.warning("Invalid 'hotkeys' in config; using default.")
        cfg["hotkeys"] = copy.deepcopy(hotkeys_defaults)

    # ---- v1.7 additions (all additive; absent/invalid -> safe defaults) ----

    ui_raw = raw.get("ui", DEFAULT_CONFIG["ui"])
    ui_defaults = DEFAULT_CONFIG["ui"]
    if isinstance(ui_raw, dict):
        selected_page = ui_raw.get("selected_page")
        appearance = ui_raw.get("appearance")
        bool_keys = ("hud_always_visible", "reduced_motion", "seen_shortcut_notice_v2")
        cfg["ui"] = {
            "selected_page": selected_page if selected_page in UI_PAGES else ui_defaults["selected_page"],
            "appearance": appearance if appearance in UI_APPEARANCE_VALUES else ui_defaults["appearance"],
            **{
                key: ui_raw[key] if isinstance(ui_raw.get(key), bool) else ui_defaults[key]
                for key in bool_keys
            },
        }
    else:
        log.warning("Invalid 'ui' in config; using default.")
        cfg["ui"] = copy.deepcopy(ui_defaults)

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


def load_history(path: Path | None = None) -> list[str]:
    """Load the persisted applied-wallpaper history ring (oldest first,
    most recently applied last). Separate from config.json so a corrupt
    or missing state file never affects settings load."""
    state_path = path if path is not None else PLAYBACK_STATE_PATH
    if state_path.exists():
        try:
            raw = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                entries = raw.get("history", [])
                if isinstance(entries, list) and all(isinstance(p, str) for p in entries):
                    return entries[-HISTORY_MAX:]
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not read playback history (%s); starting empty.", exc)
    return []


def save_history(history: Sequence[str], path: Path | None = None) -> None:
    """Atomically persist the applied-wallpaper history ring, same
    unique-temp-file pattern as save_config (safe under two instances)."""
    state_path = path if path is not None else PLAYBACK_STATE_PATH
    fd, tmp_name = tempfile.mkstemp(
        prefix=state_path.stem + ".", suffix=".tmp", dir=str(state_path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        data = json.dumps({"history": list(history)}, indent=2)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp_path, state_path)
    except OSError as exc:
        log.error("Could not save playback history: %s", exc)
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
    def __init__(self, start_minimized: bool = False, mutex_handle: Any = None) -> None:
        super().__init__()
        self._start_minimized = start_minimized
        # Held for the process lifetime once __main__ has already claimed
        # single-instance ownership via ipc.try_become_primary(); released
        # on close so a later launch can become primary in turn.
        self._mutex_handle = mutex_handle
        self._ipc_server: Optional[ipc.IpcServer] = None
        self._hotkey_listener: Optional[hotkeys.HotkeyListener] = None
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME}  —  {TAGLINE}")
        self.geometry("1180x620")
        self.minsize(980, 560)

        self.cfg = load_config()
        # Must follow cfg load (the saved preference) but precede any
        # widget construction below (CTk reads appearance mode per-widget
        # at creation time). Previously hardcoded to "dark" regardless of
        # the saved preference — folded into the same fix that honours
        # SPI_GETHIGHCONTRAST (notes_007 §1.4).
        self._apply_appearance_mode()
        self.images: list[str] = []
        self.index: int = -1
        self._active_kind: str = "folder"
        self._active_id: Optional[str] = None
        # Populated off the Tk thread by _reconnect_tick's background probe.
        # Empty at startup — folder_display_label/playlist_folder_status
        # treat a missing key as "online" (True) rather than pessimistically
        # badging every folder offline before the first probe completes.
        self._folder_online_cache: dict[str, bool] = {}
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
        # v2.0 experimental — lazily constructed only if wallpaper_target
        # is switched to "com"; never touched by the default "spi" path.
        self._com_backend: Any = None
        self._target_monitor_label_to_id: dict[str, Optional[str]] = {"All Displays": None}
        self._preview_ref = None  # keep CTkImage alive
        self._inspecting = False
        self._inspection_window: Any = None
        self._pre_inspection_geometry: Optional[str] = None
        self._slideshow_job: Any = None
        # A 1 Hz heartbeat polls these due-times rather than arming one long
        # single-shot after() — that way a sleep/hibernate gap finds "due"
        # true at most once on the next poll instead of Tk trying to fire a
        # backlog of missed intervals. Interval mode uses monotonic time
        # (immune to wall-clock/DST changes); daily mode keeps the existing
        # wall-clock trigger so its self-correcting DST behaviour (v1.4) is
        # unchanged. Exactly one of the two is set at a time.
        self._next_due_mono: Optional[float] = None
        self._next_due_wall: Optional[datetime] = None
        self._save_job: Any = None
        self._shuffle_order: list[int] = []
        self._shuffle_cursor: int = 0
        self._history: deque[str] = deque(load_history(), maxlen=HISTORY_MAX)
        self._load_token: int = 0
        self._preview_size: tuple[int, int] = (PREVIEW_W, PREVIEW_H)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dv-img")
        self._preview_future: Any = None
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
        self._start_ipc_server()
        self._start_hotkeys()
        if self._start_minimized:
            if self._tray_is_ready():
                self.withdraw()
            else:
                log.warning(
                    "--minimized requested but the tray icon isn't ready; showing window."
                )

    # ---------------- Keyboard shortcuts ----------------

    # winfo_class() names for widgets that consume typed characters.
    # CTkEntry/CTkTextbox are composites that wrap a real Tk Entry/Text as
    # an internal child — focus_get() during typing returns that child
    # directly (class "Entry"/"Text"), not the CTk wrapper (notes_006 §2.7).
    _TEXT_ENTRY_CLASSES = frozenset({"Entry", "TEntry", "Text", "Spinbox", "TSpinbox", "TCombobox"})

    def _focus_is_text_entry(self) -> bool:
        """True if the currently focused widget is a text-entry control (or
        a child of one, walking a bounded number of ancestors to cover a
        composite's internal wrapping)."""
        widget = self.focus_get()
        for _ in range(6):
            if widget is None:
                return False
            try:
                if widget.winfo_class() in self._TEXT_ENTRY_CLASSES:
                    return True
            except Exception:
                return False
            widget = getattr(widget, "master", None)
        return False

    def _shortcut(self, action: Callable[[], None]) -> Callable[[Any], Optional[str]]:
        """Wrap a single-key/no-modifier toplevel shortcut so it's a no-op
        while focus is inside a text-entry control, instead of also firing
        on every keystroke typed there. Returning None (not "break") lets
        the keystroke continue on to the entry normally in that case."""

        def handler(event: Any) -> Optional[str]:
            if self._focus_is_text_entry():
                return None
            action()
            return "break"

        return handler

    # ---------------- UI construction ----------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_stage()

        # Keyboard shortcuts — guarded against text-entry focus (see
        # _shortcut/_focus_is_text_entry): CTkEntry/CTkTextbox wrap a real
        # Tk Entry/Text internally, and a plain self.bind() on the toplevel
        # still fires on every keystroke typed there too (notes_006 P1 —
        # typing "forest" into the tag field used to also trigger Favourite
        # on 'f' and Random on 'r'). Mapping per notes_006 §2.7: Space now
        # starts/stops the slideshow (was Next) and Esc closes the popover
        # chain (was Stop) — a deliberate, documented behaviour change; see
        # _maybe_show_shortcut_notice for the one-time notice this ships
        # with, and the Playback page's Start/Stop button for the always-
        # visible non-keyboard Stop control notes_006 asks to keep.
        self.bind("<Left>", self._shortcut(self._prev))
        self.bind("<Right>", self._shortcut(self._next))
        self.bind("<Return>", self._shortcut(self._set_wallpaper))
        self.bind("<space>", self._shortcut(self._toggle_slideshow))
        self.bind("<BackSpace>", self._shortcut(self._prev))
        self.bind("p", self._shortcut(self._prev))
        self.bind("<Escape>", self._shortcut(self._on_escape))
        self.bind("r", self._shortcut(self._random))
        self.bind("R", self._shortcut(self._random))
        self.bind("f", self._shortcut(self._toggle_favourite))
        self.bind("F", self._shortcut(self._toggle_favourite))
        self.bind("h", self._shortcut(self._hide_current))
        self.bind("<F6>", self._shortcut(lambda: self.hud.reveal(keyboard=True)))
        self.bind("<F11>", self._shortcut(self._toggle_inspection_mode))
        self.bind("?", self._shortcut(self._toggle_shortcut_help))
        self.bind("<Control-z>", self._shortcut(self._history_back))
        self.bind("<Control-Z>", self._shortcut(self._history_back))

        # Dynamic 16:9 preview sizing
        self.preview.bind("<Configure>", self._on_preview_configure)
        self.main.bind("<Configure>", self._on_preview_configure)

        self._show_page(self.cfg["ui"]["selected_page"])
        self._update_apply_button_label()
        self.after(200, self._maybe_show_shortcut_notice)

    # ---------------- Sidebar: nav rail + four task pages ----------------

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=300, corner_radius=12)
        sidebar.grid(row=0, column=0, sticky="nsw", padx=(12, 6), pady=12)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(2, weight=1)
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text=APP_NAME, font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(16, 0), sticky="w")
        ctk.CTkLabel(sidebar, text=TAGLINE, font=ctk.CTkFont(size=12), text_color="gray70").grid(
            row=1, column=0, padx=16, pady=(0, 10), sticky="w")

        # Primary navigation (notes_006 §2.1): four task pages, created once
        # and kept alive — switching pages never restarts playback or
        # writes settings by itself, it only changes which page is raised.
        navrow = ctk.CTkFrame(sidebar, fg_color="transparent")
        navrow.grid(row=2, column=0, padx=12, pady=(2, 8), sticky="new")
        navrow.grid_columnconfigure((0, 1), weight=1)
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for i, page in enumerate(UI_PAGES):
            btn = ctk.CTkButton(
                navrow, text=UI_PAGE_LABELS[page], height=32,
                fg_color="gray30", hover_color="gray25",
                command=lambda p=page: self._show_page(p),
            )
            btn.grid(row=i // 2, column=i % 2, padx=3, pady=3, sticky="ew")
            self.nav_buttons[page] = btn
        sidebar.grid_rowconfigure(3, weight=1)

        page_area = ctk.CTkFrame(sidebar, fg_color="transparent")
        page_area.grid(row=3, column=0, sticky="nsew")
        page_area.grid_columnconfigure(0, weight=1)
        page_area.grid_rowconfigure(0, weight=1)

        # Root/nav stay fixed; each page scrolls independently if its own
        # content exceeds the available height (notes_006 §2.2 window rules).
        self.pages: dict[str, ctk.CTkScrollableFrame] = {}
        for page in UI_PAGES:
            frame = ctk.CTkScrollableFrame(page_area, fg_color="transparent")
            frame.grid(row=0, column=0, sticky="nsew")
            frame.grid_columnconfigure(0, weight=1)
            self.pages[page] = frame

        self._build_library_page(self.pages["library"])
        self._build_playback_page(self.pages["playback"])
        self._build_displays_page(self.pages["displays"])
        self._build_settings_page(self.pages["settings"])

    def _show_page(self, page: str) -> None:
        if page not in self.pages:
            page = "library"
        for name, frame in self.pages.items():
            if name == page:
                frame.grid()
            else:
                frame.grid_remove()
        for name, btn in self.nav_buttons.items():
            btn.configure(fg_color=ui_components.FOCUS if name == page else "gray30")
        self.cfg["ui"]["selected_page"] = page
        self._schedule_save()

    @staticmethod
    def _section_label(parent, text: str, *, first: bool = False) -> None:
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray60").grid(
            row=parent.grid_size()[1], column=0, padx=16, pady=(4 if first else 18, 0), sticky="w")

    def _build_library_page(self, page) -> None:
        def row() -> int:
            return page.grid_size()[1]

        self._section_label(page, "PLAYBACK SOURCE", first=True)
        self.source_var = ctk.StringVar(value="(no sources yet)")
        self.source_menu = ctk.CTkOptionMenu(
            page, variable=self.source_var, values=["(no sources yet)"],
            command=self._on_source_selected, dynamic_resizing=False)
        self.source_menu.grid(row=row(), column=0, padx=16, pady=(4, 6), sticky="ew")

        fbtns = ctk.CTkFrame(page, fg_color="transparent")
        fbtns.grid(row=row(), column=0, padx=16, sticky="ew")
        fbtns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(fbtns, text="+ Add folder", command=self._add_folder).grid(
            row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(fbtns, text="Remove", fg_color="gray30", hover_color="gray25",
                      command=self._remove_folder).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self._section_label(page, "PLAYLISTS")
        ctk.CTkButton(page, text="+ New Playlist",
                      command=lambda: self._open_playlist_editor()).grid(
            row=row(), column=0, padx=16, pady=(4, 4), sticky="ew")
        pbtns = ctk.CTkFrame(page, fg_color="transparent")
        pbtns.grid(row=row(), column=0, padx=16, sticky="ew")
        pbtns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(pbtns, text="Edit", fg_color="gray30", hover_color="gray25",
                      command=self._edit_active_playlist).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(pbtns, text="Delete", fg_color="gray30", hover_color="gray25",
                      command=self._delete_active_playlist).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self._section_label(page, "COLLECTIONS")
        ctk.CTkButton(page, text="+ New Collection",
                      command=lambda: self._open_collection_editor()).grid(
            row=row(), column=0, padx=16, pady=(4, 4), sticky="ew")
        cbtns = ctk.CTkFrame(page, fg_color="transparent")
        cbtns.grid(row=row(), column=0, padx=16, sticky="ew")
        cbtns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(cbtns, text="Edit", fg_color="gray30", hover_color="gray25",
                      command=self._edit_active_collection).grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(cbtns, text="Delete", fg_color="gray30", hover_color="gray25",
                      command=self._delete_active_collection).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self._section_label(page, "CURATION")
        self.hidden_btn = ctk.CTkButton(page, text="Hidden Items (0)", fg_color="gray30",
                                         hover_color="gray25", command=self._open_hidden_manager)
        self.hidden_btn.grid(row=row(), column=0, padx=16, pady=(4, 4), sticky="ew")

    def _build_playback_page(self, page) -> None:
        def row() -> int:
            return page.grid_size()[1]

        self._section_label(page, "SLIDESHOW", first=True)
        self.interval_var = ctk.StringVar(value=self.cfg["interval"])
        ctk.CTkOptionMenu(page, variable=self.interval_var,
                          values=list(SLIDESHOW_INTERVALS) + [CUSTOM_INTERVAL_LABEL],
                          command=self._on_interval_changed).grid(
            row=row(), column=0, padx=16, pady=(4, 6), sticky="ew")
        self.shuffle_var = ctk.BooleanVar(value=self.cfg["shuffle"])
        ctk.CTkSwitch(page, text="Shuffle", variable=self.shuffle_var,
                      command=self._on_shuffle_changed).grid(row=row(), column=0, padx=16, sticky="w")
        self.slide_btn = ctk.CTkButton(
            page, text="Start Slideshow", height=40, fg_color="#2e7d32", hover_color="#27682a",
            command=self._toggle_slideshow)
        self.slide_btn.grid(row=row(), column=0, padx=16, pady=(12, 0), sticky="ew")

        self._section_label(page, "SCHEDULE")
        self.schedule_mode_var = ctk.StringVar(
            value=SCHEDULE_MODE_LABELS.get(self.cfg["schedule"]["mode"], "Fixed interval"))
        ctk.CTkOptionMenu(page, variable=self.schedule_mode_var,
                          values=list(SCHEDULE_MODE_LABELS.values()),
                          command=self._on_schedule_mode_changed).grid(
            row=row(), column=0, padx=16, pady=(4, 4), sticky="ew")
        self.daily_times_var = ctk.StringVar(value=", ".join(self.cfg["schedule"]["daily_times"]))
        self.daily_times_entry = ctk.CTkEntry(
            page, textvariable=self.daily_times_var, placeholder_text="e.g. 08:00, 18:00")
        self.daily_times_entry.grid(row=row(), column=0, padx=16, sticky="ew")
        ctk.CTkButton(page, text="Apply times", fg_color="gray30", hover_color="gray25",
                      command=self._on_daily_times_apply).grid(
            row=row(), column=0, padx=16, pady=(4, 6), sticky="ew")
        self.solar_enabled_var = ctk.BooleanVar(value=self.cfg["solar"]["enabled"])
        ctk.CTkSwitch(page, text="Use solar location (else fallback times)",
                      variable=self.solar_enabled_var,
                      command=self._on_solar_settings_changed).grid(
            row=row(), column=0, padx=16, pady=(2, 0), sticky="w")
        self.solar_coords_var = ctk.StringVar(value=self._format_solar_coords())
        self.solar_coords_entry = ctk.CTkEntry(
            page, textvariable=self.solar_coords_var,
            placeholder_text="latitude, longitude e.g. 51.5074, -0.1278")
        self.solar_coords_entry.grid(row=row(), column=0, padx=16, sticky="ew")
        ctk.CTkButton(page, text="Apply location", fg_color="gray30", hover_color="gray25",
                      command=self._on_solar_coords_apply).grid(
            row=row(), column=0, padx=16, pady=(4, 0), sticky="ew")

        # Advanced disclosure (notes_006 §2.1): battery/fullscreen pause
        # policies are infrequent configuration, kept out of the daily path.
        self._power_advanced_visible = False
        self.power_advanced_toggle_btn = ctk.CTkButton(
            page, text="▸ Advanced (Battery Saver / fullscreen)", fg_color="transparent",
            hover_color="gray20", anchor="w", command=self._toggle_power_advanced)
        self.power_advanced_toggle_btn.grid(row=row(), column=0, padx=12, pady=(14, 0), sticky="ew")
        self.power_advanced_frame = ctk.CTkFrame(page, fg_color="transparent")
        self.power_advanced_frame.grid(row=row(), column=0, padx=4, pady=(0, 4), sticky="ew")
        self.power_advanced_frame.grid_columnconfigure(0, weight=1)
        self.battery_pause_var = ctk.BooleanVar(value=self.cfg["power"]["pause_on_battery_saver"])
        ctk.CTkSwitch(self.power_advanced_frame, text="Pause on Battery Saver",
                      variable=self.battery_pause_var,
                      command=self._on_power_settings_changed).grid(
            row=0, column=0, padx=12, pady=(4, 0), sticky="w")
        self.fullscreen_pause_var = ctk.BooleanVar(value=self.cfg["power"]["pause_on_fullscreen"])
        ctk.CTkSwitch(self.power_advanced_frame, text="Pause during fullscreen/games",
                      variable=self.fullscreen_pause_var,
                      command=self._on_power_settings_changed).grid(
            row=1, column=0, padx=12, pady=(4, 6), sticky="w")
        self.power_advanced_frame.grid_remove()

    def _toggle_power_advanced(self) -> None:
        self._power_advanced_visible = not self._power_advanced_visible
        if self._power_advanced_visible:
            self.power_advanced_frame.grid()
            self.power_advanced_toggle_btn.configure(text="▾ Advanced (Battery Saver / fullscreen)")
        else:
            self.power_advanced_frame.grid_remove()
            self.power_advanced_toggle_btn.configure(text="▸ Advanced (Battery Saver / fullscreen)")

    def _build_displays_page(self, page) -> None:
        def row() -> int:
            return page.grid_size()[1]

        self._section_label(page, "FIT STYLE", first=True)
        self.style_var = ctk.StringVar(value=self.cfg["style"])
        ctk.CTkOptionMenu(page, variable=self.style_var, values=list(WALLPAPER_STYLES),
                          command=self._on_style_changed).grid(
            row=row(), column=0, padx=16, pady=(4, 0), sticky="ew")
        ctk.CTkLabel(page, text="Applies to all displays — a per-monitor fit\npolicy needs pre-rendered crops (v2.0).",
                     font=ctk.CTkFont(size=10), text_color="gray60", justify="left").grid(
            row=row(), column=0, padx=16, pady=(2, 0), sticky="w")

        self._section_label(page, "MONITORS (read-only)")
        self.monitor_canvas = Canvas(page, width=268, height=110, highlightthickness=0, bg="#2b2b2b")
        self.monitor_canvas.grid(row=row(), column=0, padx=16, pady=(4, 0), sticky="ew")
        ctk.CTkButton(page, text="Refresh", fg_color="gray30", hover_color="gray25", width=80,
                      command=self._refresh_monitor_topology).grid(
            row=row(), column=0, padx=16, pady=(4, 0), sticky="w")
        self._refresh_monitor_topology()

        # Experimental per-monitor engine (v2.0) — opt-in, defaults off.
        # Verified on this development machine's single display that the
        # COM plumbing itself works (object creation, enumeration, apply);
        # true per-monitor independence needs real multi-monitor hardware
        # to confirm, which this build has not had access to. The Win32
        # topology strip above and this COM picker enumerate independently
        # and are NOT reconciled to the same display identity (notes_006
        # P1) — do not assume a visually-matching number is the same
        # display in both; that reconciliation is why the topology strip
        # stays read-only rather than becoming a clickable target picker.
        self._section_label(page, "DISPLAY ENGINE (experimental)")
        self.com_target_var = ctk.BooleanVar(value=self.cfg.get("wallpaper_target") == "com")
        self.com_target_switch = ctk.CTkSwitch(
            page, text="Per-monitor engine (COM)", variable=self.com_target_var,
            command=self._on_wallpaper_target_changed)
        self.com_target_switch.grid(row=row(), column=0, padx=16, pady=(4, 4), sticky="w")
        if windows_wallpaper_com is None:
            self.com_target_switch.configure(state="disabled")
        self.target_monitor_var = ctk.StringVar(value="All Displays")
        self.target_monitor_menu = ctk.CTkOptionMenu(
            page, variable=self.target_monitor_var, values=["All Displays"],
            command=self._on_target_monitor_selected)
        self.target_monitor_menu.grid(row=row(), column=0, padx=16, pady=(0, 4), sticky="ew")
        if self.cfg.get("wallpaper_target") == "com":
            self._refresh_com_monitor_menu()

    def _build_settings_page(self, page) -> None:
        def row() -> int:
            return page.grid_size()[1]

        self._section_label(page, "APPEARANCE", first=True)
        self.appearance_var = ctk.StringVar(
            value=UI_APPEARANCE_LABELS.get(self.cfg["ui"]["appearance"], "Dark"))
        ctk.CTkOptionMenu(page, variable=self.appearance_var,
                          values=[UI_APPEARANCE_LABELS[v] for v in UI_APPEARANCE_VALUES],
                          command=self._on_appearance_changed).grid(
            row=row(), column=0, padx=16, pady=(4, 4), sticky="ew")
        self.hud_always_visible_var = ctk.BooleanVar(value=self.cfg["ui"]["hud_always_visible"])
        ctk.CTkSwitch(page, text="Always show preview controls", variable=self.hud_always_visible_var,
                      command=self._on_hud_always_visible_changed).grid(
            row=row(), column=0, padx=16, pady=(2, 6), sticky="w")

        self._section_label(page, "HOTKEYS")
        self.hotkeys_enabled_var = ctk.BooleanVar(value=self.cfg["hotkeys"]["enabled"])
        self.hotkeys_switch = ctk.CTkSwitch(
            page, text="Global hotkeys enabled", variable=self.hotkeys_enabled_var,
            command=self._on_hotkeys_enabled_changed)
        self.hotkeys_switch.grid(row=row(), column=0, padx=16, pady=(4, 0), sticky="w")
        if not hotkeys.is_available():
            self.hotkeys_switch.configure(state="disabled")
        self.hotkeys_status_label = ctk.CTkLabel(
            page, text="", text_color="gray60", font=ctk.CTkFont(size=10),
            wraplength=260, justify="left")
        self.hotkeys_status_label.grid(row=row(), column=0, padx=16, pady=(2, 0), sticky="w")
        ctk.CTkButton(page, text="Local shortcut reference (?)", fg_color="gray30", hover_color="gray25",
                      command=self._toggle_shortcut_help).grid(
            row=row(), column=0, padx=16, pady=(6, 0), sticky="ew")

        self._section_label(page, "STARTUP")
        self.startup_var = ctk.BooleanVar(value=False)
        self.startup_switch = ctk.CTkSwitch(
            page, text="Start with Windows (minimised)", variable=self.startup_var,
            command=self._on_startup_toggle)
        self.startup_switch.grid(row=row(), column=0, padx=16, pady=(4, 0), sticky="w")
        if winreg is None or sys.platform != "win32":
            self.startup_switch.configure(state="disabled")

        self._section_label(page, "ABOUT")
        ctk.CTkLabel(
            page, text="\n".join(ABOUT_COPY),
            text_color="gray60", font=ctk.CTkFont(size=11), justify="left", anchor="w",
        ).grid(row=row(), column=0, padx=16, pady=(4, 6), sticky="w")
        ctk.CTkButton(
            page, text="Licence notice", fg_color="gray30", hover_color="gray25",
            command=self._open_licence_notice,
        ).grid(row=row(), column=0, padx=16, pady=(0, 14), sticky="ew")

    # ---------------- Main stage: header / preview / HUD / footer ----------------

    def _build_stage(self) -> None:
        self.main = ctk.CTkFrame(self, corner_radius=12)
        self.main.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        # Context header (44px): active source + a non-hover HUD reveal
        # route (notes_006 §2.2 HUD state machine point 6).
        header = ctk.CTkFrame(self.main, fg_color="transparent", height=44)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)
        self.source_context_label = ctk.CTkLabel(
            header, text="", anchor="w", font=ctk.CTkFont(size=13, weight="bold"))
        self.source_context_label.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(header, text="Controls", width=90, height=28, fg_color="gray30",
                      hover_color="gray25", command=lambda: self.hud.reveal(keyboard=True)).grid(
            row=0, column=1, sticky="e", padx=(8, 0))

        # Stage (expands): preview + floating HUD/toast/tag-drawer overlays.
        self.stage = ctk.CTkFrame(self.main, fg_color="transparent")
        self.stage.grid(row=1, column=0, sticky="nsew", padx=16, pady=4)
        self.stage.grid_columnconfigure(0, weight=1)
        self.stage.grid_rowconfigure(0, weight=1)

        self.preview = ctk.CTkLabel(
            self.stage, text="Add a folder to begin", text_color="gray50",
            font=ctk.CTkFont(size=16), corner_radius=10, fg_color=("#ECECEC", "#202020"))
        self.preview.grid(row=0, column=0, sticky="nsew")

        self.stage_tags_label = ctk.CTkLabel(
            self.stage, text="", text_color=("gray30", "gray80"), font=ctk.CTkFont(size=11),
            fg_color=ui_components.SURFACE, corner_radius=8)
        self.stage_tags_label.place(relx=0.0, rely=0.0, x=10, y=10, anchor="nw")

        self.hud = ui_components.HoverHUD(
            self.stage,
            {
                "◀ Prev": self._prev,
                "Random": self._random,
                "Next ▶": self._next,
                "♡ Favourite": self._toggle_favourite,
                "Hide": self._hide_current,
                "Tags": self._open_tag_inspector,
                "More": self._open_more_menu,
            },
            always_visible=self.cfg["ui"]["hud_always_visible"],
        )
        self.fav_btn = self.hud.buttons["♡ Favourite"]

        self.toasts = ui_components.ToastManager(self.stage)

        self._build_tag_drawer(self.stage)
        self._build_shortcut_help(self.stage)

        # Footer (52px): filename/status left, Apply right (notes_006 §2.1
        # "permanent stage footer" — stable, keyboard-reachable, outside
        # any scroll region, never a side effect of navigation alone).
        footer = ctk.CTkFrame(self.main, fg_color="transparent", height=56)
        footer.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 12))
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_propagate(False)
        meta_col = ctk.CTkFrame(footer, fg_color="transparent")
        meta_col.grid(row=0, column=0, sticky="w")
        self.meta = ctk.CTkLabel(meta_col, text="", text_color="gray60",
                                 font=ctk.CTkFont(size=12), anchor="w")
        self.meta.grid(row=0, column=0, sticky="w")
        self.status = ctk.CTkLabel(meta_col, text="Ready.", text_color="gray60",
                                   font=ctk.CTkFont(size=11), anchor="w", wraplength=440, justify="left")
        self.status.grid(row=1, column=0, sticky="w")
        self.set_btn = ctk.CTkButton(
            footer, text="Apply to all displays", height=40, width=176,
            font=ctk.CTkFont(size=14, weight="bold"), command=self._set_wallpaper)
        self.set_btn.grid(row=0, column=1, rowspan=2, sticky="e")

    def _build_tag_drawer(self, stage) -> None:
        self._tag_drawer_path: Optional[str] = None
        self.tag_drawer = ctk.CTkFrame(
            stage, width=300, fg_color=ui_components.SURFACE, corner_radius=12,
            border_width=1, border_color=ui_components.BORDER)
        title_row = ctk.CTkFrame(self.tag_drawer, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(title_row, text="Tags", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, sticky="w")
        ui_components.ActionButton(title_row, text="Close", width=60,
                                   command=self._close_tag_inspector).grid(row=0, column=1)
        self.tag_selector = ui_components.TagSelector(
            self.tag_drawer, on_change=self._on_tag_selector_change,
            on_close_requested=self._close_tag_inspector)
        self.tag_selector.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

    def _build_shortcut_help(self, stage) -> None:
        self.shortcut_help = ctk.CTkFrame(
            stage, fg_color=ui_components.SURFACE, corner_radius=12,
            border_width=1, border_color=ui_components.BORDER)
        title_row = ctk.CTkFrame(self.shortcut_help, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(title_row, text="Keyboard shortcuts",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")
        ui_components.ActionButton(title_row, text="Close", width=60,
                                   command=self._toggle_shortcut_help).grid(row=0, column=1)
        lines = [
            ("Left / Right", "Previous / Next selected preview (no apply)"),
            ("R", "Random preview selection"),
            ("F", "Toggle favourite"),
            ("H", "Hide selected image"),
            ("Enter", "Apply selection"),
            ("Space", "Start / Stop slideshow"),
            ("F6", "Reveal preview controls"),
            ("F11", "Inspection mode (fullscreen preview)"),
            ("Ctrl+Z", "Undo last applied wallpaper"),
            ("Esc", "Close this / the active panel"),
            ("?", "Toggle this help"),
        ]
        body = ctk.CTkFrame(self.shortcut_help, fg_color="transparent")
        body.grid(row=1, column=0, padx=14, pady=(0, 14), sticky="ew")
        for i, (key, desc) in enumerate(lines):
            ctk.CTkLabel(body, text=key, font=ctk.CTkFont(size=12, weight="bold"), width=90,
                         anchor="w").grid(row=i, column=0, sticky="w", pady=1)
            ctk.CTkLabel(body, text=desc, font=ctk.CTkFont(size=12), text_color="gray70",
                         anchor="w").grid(row=i, column=1, sticky="w", pady=1)
        self._shortcut_help_visible = False

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

        # Only join against COM if its backend already exists — this
        # read-only label must never be the reason a COM STA thread gets
        # started for someone who has not opted into the experimental
        # per-monitor engine (notes_007 §1.3). Still no click handler:
        # a resolved join only improves the label, never becomes a target.
        com_monitors: list[tuple[str, tuple[int, int, int, int]]] = []
        if self._com_backend is not None:
            try:
                com_monitors = self._com_backend.enumerate_monitors()
            except Exception as exc:
                log.warning("Could not enumerate COM monitors for topology join: %s", exc)
        joins = join_monitor_topology(monitors, com_monitors) if com_monitors else [None] * len(monitors)

        for i, (monitor, com_index) in enumerate(zip(layout, joins), start=1):
            box = monitor["layout"]
            x0, y0 = margin + box["x"], margin + box["y"]
            x1, y1 = x0 + box["w"], y0 + box["h"]
            color = "#3a8dde" if monitor["primary"] else "#5a5a5a"
            canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="#1c1c1c")
            if com_index is not None:
                label = f"Display {com_index + 1}"
            elif com_monitors:
                label = f"{i} (unresolved)"
            else:
                label = f"{i}"
            label += " ★" if monitor["primary"] else ""
            canvas.create_text(
                (x0 + x1) // 2, (y0 + y1) // 2, text=label, fill="white",
                font=("Segoe UI", 9, "bold"),
            )

    # ---------------- Experimental per-monitor engine (v2.0) ----------------

    def _get_com_backend(self):
        """Lazily construct the COM backend's dedicated STA thread — only
        ever called once wallpaper_target is switched to "com"."""
        if windows_wallpaper_com is None:
            return None
        if self._com_backend is None:
            try:
                self._com_backend = windows_wallpaper_com.ComWallpaperBackend()
            except Exception as exc:
                log.warning("Could not start COM wallpaper backend: %s", exc)
                return None
        return self._com_backend

    def _refresh_com_monitor_menu(self) -> None:
        backend = self._get_com_backend()
        labels = ["All Displays"]
        mapping: dict[str, Optional[str]] = {"All Displays": None}
        if backend is not None:
            try:
                for i, (device_id, _rect) in enumerate(backend.enumerate_monitors(), start=1):
                    label = f"Display {i}"
                    labels.append(label)
                    mapping[label] = device_id
            except Exception as exc:
                log.warning("Could not enumerate COM monitors: %s", exc)
        self._target_monitor_label_to_id = mapping
        self.target_monitor_menu.configure(values=labels)
        if self.target_monitor_var.get() not in labels:
            self.target_monitor_var.set(labels[0])

    def _on_wallpaper_target_changed(self) -> None:
        enabled = bool(self.com_target_var.get())
        self.cfg["wallpaper_target"] = "com" if enabled else "spi"
        self._flush_save()
        if enabled:
            self._refresh_com_monitor_menu()
            self._set_status(
                "Experimental per-monitor engine on — verified on this build's own "
                "hardware only for the all-displays target; check a specific-monitor "
                "target carefully on yours."
            )
        else:
            self._set_status("Wallpaper engine: standard (all displays).")
        self._update_apply_button_label()

    def _on_target_monitor_selected(self, _label: str) -> None:
        self._update_apply_button_label()

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
        """Persistent status line in the stage footer — running/paused/
        offline state, always visible outside any scroll region. Kept as
        the compatibility bridge notes_006 §4 describes: most call sites
        are unclassified between "ongoing state" and "transient result",
        so this stays authoritative and _toast() is layered on top for the
        subset of call sites that are clearly one-off confirmations."""
        self.status.configure(text=text)

    def _toast(self, text: str, *, error: bool = False) -> None:
        """Post a transient confirmation alongside the persistent status
        line above — never a replacement for it. Silently no-ops if the
        toast manager doesn't exist yet (very early startup) or its bounded
        queue is full; the persistent status line is always the fallback
        record, so a dropped toast never loses information."""
        toasts = getattr(self, "toasts", None)
        if toasts is not None:
            toasts.post(ui_components.Notice(text, error=error))

    def _update_apply_button_label(self) -> None:
        if self.cfg.get("wallpaper_target") == "com":
            target = self.target_monitor_var.get()
            text = "Apply to all displays" if target == "All Displays" else f"Apply to {target}"
        else:
            text = "Apply to all displays"
        self.set_btn.configure(text=text)

    def _update_header_context(self) -> None:
        if self._active_id is None:
            label = "No source selected"
        else:
            label = source_display_label(self.cfg, self._active_kind, self._active_id, self._folder_online_cache)
        count = f"{len(self.images)} images" if self.images else "no images"
        self.source_context_label.configure(text=f"{label} · {count}")

    def _restyle_canvas_widgets(self) -> None:
        """Update raw-Tk Canvas widgets when appearance changes — CTk's
        colour tuples don't reach native Canvas primitives (notes_006
        §2.6)."""
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "#2b2b2b" if is_dark else "#e5e5e5"
        try:
            self.monitor_canvas.configure(bg=bg)
        except Exception:
            pass

    def _apply_appearance_mode(self) -> None:
        """Resolve and apply the live CTk appearance mode. Windows' Ease of
        Access > High contrast is a separate, OS-level setting; when it's
        on we defer to CTk's own "system" mode rather than fight it with a
        saved light/dark preference the user picked before turning high
        contrast on — the preference itself is left untouched in cfg and
        takes effect again as soon as high contrast is turned off
        (notes_007 §1.4: honour it, don't invent a fourth appearance
        mode)."""
        if is_high_contrast_active():
            ctk.set_appearance_mode("system")
        else:
            ctk.set_appearance_mode(self.cfg["ui"]["appearance"])

    def _on_appearance_changed(self, value: str) -> None:
        mode = UI_APPEARANCE_LABEL_TO_VALUE.get(value, "dark")
        self.cfg["ui"]["appearance"] = mode
        self._flush_save()
        self._apply_appearance_mode()
        self._restyle_canvas_widgets()

    def _on_hud_always_visible_changed(self) -> None:
        value = bool(self.hud_always_visible_var.get())
        self.cfg["ui"]["hud_always_visible"] = value
        self._flush_save()
        self.hud.set_always_visible(value)

    def _open_more_menu(self) -> None:
        """A small overflow menu for infrequent stage actions (notes_006
        §2.2): a plain native tk.Menu, not a CTk widget — this is a
        discrete action list, not something that benefits from a custom
        popover, and native menus already have working keyboard/Narrator
        support that a hand-rolled one would have to rebuild."""
        menu = Menu(self, tearoff=False)
        menu.add_command(label="Reveal in Explorer", command=self._reveal_current_in_explorer)
        menu.add_command(label="Copy Path", command=self._copy_current_path)
        menu.add_command(label="Undo Last Applied", command=self._history_back)
        menu.add_command(label="Hidden Items", command=self._open_hidden_manager)
        more_btn = self.hud.buttons.get("More")
        if more_btn is None:
            return
        x = more_btn.winfo_rootx()
        y = more_btn.winfo_rooty()
        try:
            menu.tk_popup(x, y - 8)
        finally:
            menu.grab_release()

    def _copy_current_path(self) -> None:
        if not (0 <= self.index < len(self.images)):
            self._toast("Nothing selected.", error=True)
            return
        path = self.images[self.index]
        self.clipboard_clear()
        self.clipboard_append(path)
        self._toast(f"Copied path: {Path(path).name}")

    # ---------------- Shortcut help, inspection mode, Escape chain ----------------

    def _toggle_shortcut_help(self) -> None:
        self._shortcut_help_visible = not self._shortcut_help_visible
        if self._shortcut_help_visible:
            self.shortcut_help.place(relx=0.5, rely=0.5, anchor="c")
            self.shortcut_help.lift()
        else:
            self.shortcut_help.place_forget()
            self.focus_set()

    def _maybe_show_shortcut_notice(self) -> None:
        """One-time notice for the Space/Esc remap (notes_006 §2.7: "ship
        a one-time shortcut notice"). Space now starts/stops the slideshow
        instead of advancing; Esc now closes panels instead of stopping
        the slideshow — the Playback page's Start/Stop button remains the
        always-visible non-keyboard way to stop it."""
        if self.cfg["ui"]["seen_shortcut_notice_v2"]:
            return
        self.cfg["ui"]["seen_shortcut_notice_v2"] = True
        self._schedule_save()
        self._toast(
            "Shortcuts updated: Space now Starts/Stops the slideshow (was Next); "
            "Esc now closes panels (was Stop). Press ? for the full list.",
            error=False,
        )

    def _on_escape(self) -> None:
        """Esc closes the active panel/popover, innermost first, rather
        than stopping the slideshow (notes_006 §2.7 — a deliberate remap;
        see _maybe_show_shortcut_notice). Falls through to nothing rather
        than a destructive/global action if nothing is open."""
        if self._inspecting:
            self._toggle_inspection_mode()
        elif self._shortcut_help_visible:
            self._toggle_shortcut_help()
        elif self._tag_drawer_path is not None:
            self._close_tag_inspector()

    def _toggle_inspection_mode(self) -> None:
        """Borderless fit-to-screen preview (notes_006 §2.2). Zoom/pan is
        explicitly out of scope for this pass — the document itself
        defers it behind a separate bounded higher-resolution decode
        request; this only ever shows the already-decoded preview image
        scaled to the inspection window."""
        if self._inspecting:
            self._close_inspection_mode()
        else:
            self._open_inspection_mode()

    def _open_inspection_mode(self) -> None:
        if not (0 <= self.index < len(self.images)) or self._preview_ref is None:
            self._toast("Nothing to inspect.", error=True)
            return
        self._inspecting = True
        self._pre_inspection_geometry = self.geometry()
        win = ctk.CTkToplevel(self)
        win.attributes("-fullscreen", True)
        win.configure(fg_color="black")
        win.title(f"{APP_NAME} — Inspection")
        label = ctk.CTkLabel(win, text="", image=self._preview_ref)
        label.pack(expand=True, fill="both")
        hint = ctk.CTkLabel(win, text="Preview only · Esc to exit", text_color="gray70",
                            font=ctk.CTkFont(size=12), fg_color="black")
        hint.place(relx=0.5, rely=1.0, anchor="s", y=-14)
        win.bind("<Escape>", lambda e: self._close_inspection_mode())
        win.bind("<F11>", lambda e: self._close_inspection_mode())
        win.focus_force()
        self._inspection_window = win

    def _close_inspection_mode(self) -> None:
        win = getattr(self, "_inspection_window", None)
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass
            self._inspection_window = None
        self._inspecting = False
        self.focus_set()

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
            if kind == "collection" and find_collection(self.cfg, sid) is not None:
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
            label = folder_display_label(folder, self._folder_online_cache)
            labels.append(label)
            mapping[label] = ("folder", folder)
        for playlist in self.cfg["playlists"]:
            label = source_display_label(self.cfg, "playlist", playlist["id"], self._folder_online_cache)
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
        self._update_header_context()
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
        """Modal editor for creating or renaming/re-scoping a playlist. The
        draft dict is mutated only by this dialog's own widgets and
        committed to cfg solely inside do_save — Cancel (or Esc, or the
        window's close button) is always a true no-op on the playlist
        itself (notes_007 §1.1). "Browse…" is the one exception: adding a
        library folder from here is the same action as the Library page's
        Add Folder, so it commits to cfg["folders"] immediately, same as
        that existing picker (notes_007 §1.1 P1)."""
        draft = {
            "name": playlist["name"] if playlist else "",
            "folders": list(playlist["folders"]) if playlist else [],
        }
        sheet = ui_components.EditorSheet(
            self,
            title="New Playlist" if playlist is None else f"Edit Playlist — {playlist['name']}",
            on_save=lambda: do_save(),
            geometry="420x520",
        )
        body = sheet.body
        body.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(body, text="Playlist name").grid(row=0, column=0, sticky="w", pady=(0, 4))
        name_var = ctk.StringVar(value=draft["name"])
        ctk.CTkEntry(body, textvariable=name_var).grid(row=1, column=0, sticky="ew")

        folders_row = ctk.CTkFrame(body, fg_color="transparent")
        folders_row.grid(row=2, column=0, sticky="ew", pady=(16, 4))
        folders_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(folders_row, text="Folders to include").grid(row=0, column=0, sticky="w")
        ctk.CTkButton(folders_row, text="Browse…", width=90, command=lambda: do_browse()).grid(
            row=0, column=1, sticky="e")

        scroll = ctk.CTkScrollableFrame(body, height=260)
        scroll.grid(row=3, column=0, sticky="nsew")
        check_vars: dict[str, ctk.BooleanVar] = {}

        def rebuild_folder_list() -> None:
            for w in scroll.winfo_children():
                w.destroy()
            check_vars.clear()
            for folder in self.cfg["folders"]:
                var = ctk.BooleanVar(value=folder in draft["folders"])
                var.trace_add("write", lambda *_a: validate())
                ctk.CTkCheckBox(scroll, text=folder_display_label(folder), variable=var).pack(
                    anchor="w", pady=2, padx=4
                )
                check_vars[folder] = var
            if not self.cfg["folders"]:
                ctk.CTkLabel(scroll, text="Add a wallpaper folder first.",
                             text_color="gray60").pack(pady=8)

        def do_browse() -> None:
            chosen = filedialog.askdirectory(title="Choose a wallpaper folder", parent=sheet)
            if not chosen:
                return
            chosen = os.path.normpath(chosen)
            if chosen not in self.cfg["folders"]:
                self.cfg["folders"].append(chosen)
            if chosen not in draft["folders"]:
                draft["folders"].append(chosen)
            rebuild_folder_list()
            validate()

        def validate(*_args) -> None:
            draft["folders"] = [f for f, v in check_vars.items() if v.get()]
            name = name_var.get().strip()
            if not name:
                sheet.set_error("Playlist needs a name.")
                sheet.set_valid(False)
            elif not draft["folders"]:
                sheet.set_error("Select at least one folder.")
                sheet.set_valid(False)
            else:
                sheet.set_error("")
                sheet.set_valid(True)

        def do_save() -> Optional[str]:
            name = name_var.get().strip()
            chosen = draft["folders"]
            if not name:
                return "Playlist needs a name."
            if not chosen:
                return "Select at least one folder."
            if playlist is None:
                created = {"id": new_id(), "name": name, "folders": chosen}
                self.cfg["playlists"].append(created)
                self._load_source("playlist", created["id"])
            else:
                playlist["name"] = name
                playlist["folders"] = chosen
                if self._active_kind == "playlist" and self._active_id == playlist["id"]:
                    self._rebuild_playback_after_filter_change()
                self._refresh_source_menu()
            self._flush_save()
            return None

        rebuild_folder_list()
        name_var.trace_add("write", validate)
        validate()

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
        """Modal editor for a saved tag filter. Reuses TagSelector — the
        same exact-string canonical tag semantics as the main window's tag
        drawer — instead of a raw comma-separated box, which previously
        let whitespace/case drift between the two entry points (notes_007
        §1.1 P1). Match count runs off the Tk thread since it can touch
        list_images() I/O; a stale result (tags changed again before it
        returns) is dropped rather than repainted."""
        draft = {
            "name": collection["name"] if collection else "",
            "tags_any": list(collection["tags_any"]) if collection else [],
        }
        sheet = ui_components.EditorSheet(
            self,
            title="New Collection" if collection is None else f"Edit Collection — {collection['name']}",
            on_save=lambda: do_save(),
            geometry="380x480",
        )
        body = sheet.body

        ctk.CTkLabel(body, text="Collection name").grid(row=0, column=0, sticky="w", pady=(0, 4))
        name_var = ctk.StringVar(value=draft["name"])
        ctk.CTkEntry(body, textvariable=name_var).grid(row=1, column=0, sticky="ew")

        ctk.CTkLabel(body, text="Match images tagged with any of").grid(
            row=2, column=0, sticky="w", pady=(16, 4))
        selector = ui_components.TagSelector(
            body, known=self._all_known_tags(),
            on_change=lambda tags: on_tags_changed(tags),
            on_close_requested=sheet.cancel,
        )
        selector.grid(row=3, column=0, sticky="ew")
        selector.set_tags(draft["tags_any"])

        match_label = ctk.CTkLabel(
            body, text="", text_color="gray60", font=ctk.CTkFont(size=11), anchor="w")
        match_label.grid(row=4, column=0, sticky="ew", pady=(4, 0))

        def validate() -> None:
            name = name_var.get().strip()
            if not name:
                sheet.set_error("Collection needs a name.")
                sheet.set_valid(False)
            elif not draft["tags_any"]:
                sheet.set_error("Select at least one tag.")
                sheet.set_valid(False)
            else:
                sheet.set_error("")
                sheet.set_valid(True)

        def refresh_match_count() -> None:
            tags_snapshot = list(draft["tags_any"])
            if not tags_snapshot:
                match_label.configure(text="")
                return
            match_label.configure(text="Checking match count…")
            future = self._executor.submit(collection_match_count, self.cfg, tags_snapshot)
            future.add_done_callback(
                lambda fut: self.after(0, on_match_done, fut, tags_snapshot)
            )

        def on_match_done(future, tags_snapshot: list[str]) -> None:
            if not sheet.winfo_exists() or draft["tags_any"] != tags_snapshot:
                return  # superseded by a later edit — never paint a stale count
            try:
                count = future.result()
            except Exception as exc:
                log.warning("Collection match-count failed: %s", exc)
                return
            noun = "image" if count == 1 else "images"
            suffix = "" if count else "  (not an error — tag images first)"
            match_label.configure(text=f"{count} {noun} match{suffix}")

        def on_tags_changed(tags: tuple[str, ...]) -> None:
            draft["tags_any"] = list(tags)
            validate()
            refresh_match_count()

        def do_save() -> Optional[str]:
            name = name_var.get().strip()
            tags_any = draft["tags_any"]
            if not name:
                return "Collection needs a name."
            if not tags_any:
                return "Select at least one tag."
            if collection is None:
                created = {"id": new_id(), "name": name, "tags_any": tags_any}
                self.cfg["collections"].append(created)
                self._load_source("collection", created["id"])
            else:
                collection["name"] = name
                collection["tags_any"] = tags_any
                if self._active_kind == "collection" and self._active_id == collection["id"]:
                    self._rebuild_playback_after_filter_change()
                self._refresh_source_menu()
            self._flush_save()
            return None

        name_var.trace_add("write", lambda *_a: validate())
        validate()
        refresh_match_count()

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
        self._toast("Removed from Favourites" if is_fav else "Added to Favourites")
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
        self.hidden_btn.configure(text=f"Hidden Items ({len(self.cfg.get('hidden', []))})")

    def _update_tags_field(self) -> None:
        """Refresh the stage's subdued read-only tag summary (up to two
        tags plus "+N" — notes_006 §2.4). The editable chip list lives in
        the tag drawer (see _open_tag_inspector) and is refreshed there,
        not here, so this never emits a write."""
        tags = get_tags(self.cfg, self.images[self.index]) if 0 <= self.index < len(self.images) else []
        if not tags:
            self.stage_tags_label.configure(text="")
            return
        shown = tags[:2]
        extra = len(tags) - len(shown)
        text = "  ·  ".join(shown) + (f"   +{extra}" if extra > 0 else "")
        self.stage_tags_label.configure(text=f"  {text}  ")

    def _all_known_tags(self) -> list[str]:
        known: set[str] = set()
        for tag_list in self.cfg.get("tags", {}).values():
            known.update(tag_list)
        return sorted(known, key=str.casefold)

    def _open_tag_inspector(self) -> None:
        if not (0 <= self.index < len(self.images)):
            self._toast("Nothing selected.", error=True)
            return
        # Capture the path now: navigation while the drawer stays open must
        # not redirect a delayed tag edit onto a different image
        # (notes_006 §2.4) — every write below targets this captured path,
        # never self.images[self.index] at write time.
        self._tag_drawer_path = self.images[self.index]
        self.tag_selector.set_known(self._all_known_tags())
        self.tag_selector.set_tags(get_tags(self.cfg, self._tag_drawer_path))
        self.tag_drawer.place(relx=1.0, rely=0.0, x=-10, y=10, anchor="ne")
        self.tag_drawer.lift()
        self.hud.pinned = True
        self.hud.reveal()
        self.tag_selector.entry.focus_set()

    def _close_tag_inspector(self) -> None:
        self.tag_drawer.place_forget()
        self.hud.pinned = False
        self._tag_drawer_path = None
        self.focus_set()

    def _on_tag_selector_change(self, tags: tuple[str, ...]) -> None:
        if self._tag_drawer_path is None:
            return
        set_tags(self.cfg, self._tag_drawer_path, list(tags))
        self._schedule_save()
        if 0 <= self.index < len(self.images) and self.images[self.index] == self._tag_drawer_path:
            self._update_tags_field()

    def _rebuild_playback_after_filter_change(self, preferred_path: Optional[str] = None) -> None:
        """Recompute images/index/shuffle-deck after Hide, Unhide, or an
        editor Save that touched the active source (notes_007 §1.2). The
        old code let the shuffle deck outlive a list-length change, which
        could IndexError or silently land on the wrong file mid-slideshow —
        every mutation of `self.images` on this path must go through here
        so the deck is never stale."""
        self._load_token += 1
        old_index = self.index
        self.images = (
            resolve_source_images(self.cfg, self._active_kind, self._active_id)
            if self._active_id else []
        )
        self._shuffle_order = []
        self._shuffle_cursor = 0
        self.index = resolve_rebuilt_index(self.images, old_index, preferred_path)
        self._update_hidden_count_label()
        self._update_header_context()
        if self.index >= 0:
            self._show_current()
        else:
            self.preview.configure(image=None, text="No images left in this source")
            self.meta.configure(text="")
            self._update_favourite_button()
            self._update_tags_field()

    def _hide_current(self) -> None:
        if not (0 <= self.index < len(self.images)):
            return
        path = self.images[self.index]
        name = Path(path).name
        # Hiding the file currently on the desktop (or hiding anything while
        # the slideshow runs) must advance the desktop, not just the
        # in-window preview — otherwise "Hidden" is a lie about what's
        # actually showing (notes_007 §1.2 P1).
        replace_desktop = (
            self._slideshow_running
            or self.cfg.get("current_image") == path
            or bool(self._history and self._history[-1] == path)
        )
        set_membership(self.cfg, "hidden", path, True)
        self._rebuild_playback_after_filter_change()
        if replace_desktop:
            if 0 <= self.index < len(self.images):
                new_path = self.images[self.index]
                if self._apply_path(new_path, silent=True):
                    self._record_history(new_path)
                    self._set_status(f"Hidden {name}. Desktop updated to {Path(new_path).name}.")
                else:
                    self._set_status(f"Hidden {name}. Could not update the desktop.")
            else:
                self._set_status(f"Hidden {name}. No images left — desktop wallpaper unchanged.")
        else:
            self._set_status(f"Hidden {name}. Use \"Hidden Items\" to restore it.")
        self._toast(f"Hidden: {name}")
        self._flush_save()

    def _reveal_path_in_explorer(self, path: str) -> None:
        try:
            # Windows paths cannot contain '"', so this cannot break out of
            # the /select argument; no shell is involved (shell=False).
            subprocess.Popen(f'explorer /select,"{path}"')
        except OSError as exc:
            log.warning("Reveal in Explorer failed: %s", exc)
            self._set_status("Could not open Explorer.")

    def _open_licence_notice(self) -> None:
        """Small read-only view of the licence lead-in — not the full
        LICENSE dumped into a 260px sidebar (notes_007 §1.5). Reads the
        real file when available (dev checkout or a frozen build that
        happens to bundle it) and falls back to the baked short notice
        so this never depends on RESOURCE_DIR at paint time."""
        try:
            text = LICENSE_PATH.read_text(encoding="utf-8").strip()
        except OSError:
            text = LICENCE_NOTICE_FALLBACK
        win = ctk.CTkToplevel(self)
        win.title("Licence Notice")
        win.geometry("420x320")
        win.minsize(320, 240)
        win.transient(self)
        win.grab_set()
        box = ctk.CTkTextbox(win, wrap="word")
        box.pack(padx=16, pady=16, fill="both", expand=True)
        box.insert("1.0", text)
        box.configure(state="disabled")
        ctk.CTkButton(win, text="Close", command=win.destroy).pack(padx=16, pady=(0, 16), fill="x")

    def _open_hidden_manager(self) -> None:
        # notes_006 §2.4 P2: showing only the basename meant two files
        # named the same thing on different drives were indistinguishable.
        # Each row now shows the parent folder (with an offline badge) too,
        # plus a search filter for a long hidden list.
        win = ctk.CTkToplevel(self)
        win.title("Hidden Items")
        win.geometry("460x480")
        win.minsize(360, 320)
        win.transient(self)
        win.grab_set()

        search_var = ctk.StringVar(value="")
        ctk.CTkEntry(win, textvariable=search_var, placeholder_text="Search hidden items…").pack(
            padx=16, pady=(16, 0), fill="x")
        count_label = ctk.CTkLabel(win, text="", text_color="gray60", font=ctk.CTkFont(size=11), anchor="w")
        count_label.pack(padx=16, pady=(4, 0), fill="x")
        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(padx=16, pady=(8, 4), fill="both", expand=True)

        def rebuild(*_args) -> None:
            for w in scroll.winfo_children():
                w.destroy()
            hidden = self.cfg.get("hidden", [])
            query = search_var.get().strip().lower()
            shown = [p for p in hidden if query in p.lower()] if query else hidden
            count_label.configure(
                text=f"{len(shown)} of {len(hidden)} hidden" if query else f"{len(hidden)} hidden")
            if not shown:
                ctk.CTkLabel(scroll, text="No hidden items.", text_color="gray60").pack(pady=8)
                return
            for path in shown:
                item = ctk.CTkFrame(scroll, fg_color="transparent")
                item.pack(fill="x", pady=2)
                text_col = ctk.CTkFrame(item, fg_color="transparent")
                text_col.pack(side="left", fill="x", expand=True)
                ctk.CTkLabel(text_col, text=Path(path).name, anchor="w").pack(fill="x")
                folder = str(Path(path).parent)
                # Read from the cache the reconnect watcher already keeps
                # off-thread — probing is_folder_online() here would freeze
                # this dialog on a slow/offline NAS list (notes_007 §1.2 P2),
                # the same class of hitch v1.6 already fixed for the sidebar.
                online = self._folder_online_cache.get(folder, True)
                folder_text = folder if online else f"{folder}  (offline)"
                ctk.CTkLabel(
                    text_col, text=folder_text, anchor="w", font=ctk.CTkFont(size=10),
                    text_color="gray60" if online else "#d98c3f",
                ).pack(fill="x")

                def unhide(p=path) -> None:
                    set_membership(self.cfg, "hidden", p, False)
                    if self._active_id is not None:
                        self._rebuild_playback_after_filter_change(preferred_path=p)
                    self._flush_save()
                    rebuild()

                btn_col = ctk.CTkFrame(item, fg_color="transparent")
                btn_col.pack(side="right")
                ctk.CTkButton(
                    btn_col, text="Reveal", width=60, fg_color="gray30", hover_color="gray25",
                    command=lambda p=path: self._reveal_path_in_explorer(p),
                ).pack(side="left", padx=(0, 6))
                ctk.CTkButton(btn_col, text="Unhide", width=70, command=unhide).pack(side="left")

        def remove_missing() -> None:
            hidden_snapshot = list(self.cfg.get("hidden", []))

            def probe() -> list[str]:
                # Path.exists() is a filesystem call — for a hidden list of
                # NAS/offline paths this must stay off the Tk thread, same
                # rule as every other folder probe in this app.
                return [p for p in hidden_snapshot if not Path(p).exists()]

            future = self._executor.submit(probe)
            future.add_done_callback(lambda fut: self.after(0, on_probe_done, fut))

        def on_probe_done(future) -> None:
            if not win.winfo_exists():
                return
            try:
                missing = future.result()
            except Exception as exc:
                log.warning("Remove missing probe failed: %s", exc)
                return
            if not missing:
                messagebox.showinfo(APP_NAME, "No missing files found among hidden items.", parent=win)
                return
            if not messagebox.askyesno(
                APP_NAME,
                f"Remove {len(missing)} hidden item(s) whose files are gone?\n\n"
                "(This only removes them from the Hidden list — nothing else is touched.)",
                parent=win,
            ):
                return
            for p in missing:
                set_membership(self.cfg, "hidden", p, False)
            if self._active_id is not None:
                self._rebuild_playback_after_filter_change()
            self._flush_save()
            rebuild()

        ctk.CTkButton(
            win, text="Remove missing…", fg_color="gray30", hover_color="gray25",
            command=remove_missing,
        ).pack(padx=16, pady=(0, 12), fill="x")

        search_var.trace_add("write", rebuild)
        rebuild()

    # ---------------- Drive reconnect watcher ----------------

    def _start_reconnect_watcher(self) -> None:
        self._reconnect_job = self.after(RECONNECT_POLL_MS, self._reconnect_tick)

    def _reconnect_tick(self) -> None:
        if self._closing:
            return
        # is_folder_online()/list_images() are OS filesystem calls — for an
        # unreachable NAS/UNC path these can block for the network timeout
        # (tens of seconds), so every bit of this probe runs off the Tk
        # thread; only the *result* is marshalled back via after(0, ...).
        all_folders = dedupe_preserve_order(
            list(self.cfg["folders"])
            + [f for p in self.cfg["playlists"] for f in p.get("folders", [])]
        )
        had_no_images = not self.images
        active_kind, active_id = self._active_kind, self._active_id
        cfg_snapshot = self.cfg

        def probe() -> tuple[dict[str, bool], Optional[list[str]]]:
            online = {f: is_folder_online(f) for f in all_folders}
            images = (
                resolve_source_images(cfg_snapshot, active_kind, active_id)
                if had_no_images and active_id is not None
                else None
            )
            return online, images

        future = self._executor.submit(probe)
        future.add_done_callback(lambda fut: self.after(0, self._on_reconnect_probe_done, fut))
        self._reconnect_job = self.after(RECONNECT_POLL_MS, self._reconnect_tick)

    def _on_reconnect_probe_done(self, future) -> None:
        if self._closing:
            return
        try:
            online, images = future.result()
        except Exception as exc:
            log.warning("Reconnect probe failed: %s", exc)
            return
        self._folder_online_cache = online
        self._refresh_source_menu()  # refreshes offline badges without user action
        if images:
            self.images = images
            self.index = 0
            self._load_token += 1
            self._set_status("Source reconnected — resuming.")
            self._show_current()

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
        self._update_header_context()
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

        if self._preview_future is not None:
            # Cancels only if the previous decode hasn't started yet (a
            # no-op otherwise) — bounds the executor queue during a burst
            # of rapid navigation instead of letting hundreds of already-
            # stale decodes (their result would be dropped by the token
            # check anyway) run to completion one by one.
            self._preview_future.cancel()
        self._preview_future = self._executor.submit(work)
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
        """Fit Style is a staged preference, not an apply command. It used
        to call set_windows_wallpaper directly here — always through the
        legacy global SPI path, regardless of whether the experimental
        per-monitor COM engine and a specific target monitor were selected
        (notes_006 P1: a supposedly preparatory setting could silently
        restamp every display, bypassing the chosen COM route). style_var
        is already read at apply time by _apply_path/_set_wallpaper, so
        the new value takes effect on the next explicit apply — Set as
        Wallpaper, Enter, a slideshow tick, tray Next/Previous, IPC/hotkey
        next, etc. — with no separate propagation needed here.
        """
        self._flush_save()
        self._set_status(
            f"Fit style set to {self.style_var.get()} — used next time the wallpaper is applied."
        )

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
        self.cfg["schedule"]["mode"] = SCHEDULE_LABEL_TO_MODE.get(value, "interval")
        self._flush_save()
        if self._slideshow_running:
            self._stop_slideshow(update_status=False)
            self._start_slideshow()

    def _format_solar_coords(self) -> str:
        lat, lon = self.cfg["solar"]["latitude"], self.cfg["solar"]["longitude"]
        return f"{lat}, {lon}" if lat is not None and lon is not None else ""

    def _on_solar_settings_changed(self) -> None:
        self.cfg["solar"]["enabled"] = bool(self.solar_enabled_var.get())
        self._flush_save()
        if self._slideshow_running and self.cfg["schedule"]["mode"] == "solar":
            self._stop_slideshow(update_status=False)
            self._start_slideshow()

    def _on_solar_coords_apply(self) -> None:
        raw = self.solar_coords_var.get().strip()
        if not raw:
            self.cfg["solar"]["latitude"] = None
            self.cfg["solar"]["longitude"] = None
            self._flush_save()
            self._set_status("Solar location cleared — solar mode will use fallback times.")
            return
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) != 2:
            messagebox.showerror(APP_NAME, "Enter coordinates as: latitude, longitude")
            return
        try:
            lat, lon = float(parts[0]), float(parts[1])
        except ValueError:
            messagebox.showerror(APP_NAME, "Latitude/longitude must be numbers.")
            return
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            messagebox.showerror(APP_NAME, "Latitude must be -90..90 and longitude -180..180.")
            return
        self.cfg["solar"]["latitude"] = lat
        self.cfg["solar"]["longitude"] = lon
        self.solar_coords_var.set(f"{lat}, {lon}")
        self._flush_save()
        self._set_status("Solar location updated.")
        if self._slideshow_running and self.cfg["schedule"]["mode"] == "solar":
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

    def _apply_path(self, path: str, silent: bool) -> bool:
        """Apply *path* as the desktop wallpaper via the configured backend.
        Returns True on success. Does not touch self.index/self.images or
        the history ring — callers decide whether to sync those."""
        try:
            if self.cfg.get("wallpaper_target") == "com":
                backend = self._get_com_backend()
                if backend is None:
                    raise RuntimeError("Experimental per-monitor engine is unavailable.")
                monitor_id = self._target_monitor_label_to_id.get(self.target_monitor_var.get())
                backend.set_wallpaper(monitor_id, ensure_wallpaper_path(path), self.style_var.get())
                target_desc = "all displays" if monitor_id is None else self.target_monitor_var.get()
                self._set_status(f"Wallpaper set on {target_desc}: {Path(path).name}")
                self._toast(f"Wallpaper set on {target_desc}: {Path(path).name}")
            else:
                set_windows_wallpaper(path, self.style_var.get())
                self._set_status(f"Wallpaper set: {Path(path).name}")
                self._toast(f"Wallpaper set: {Path(path).name}")
            return True
        except Exception as exc:
            if silent:
                # Unattended slideshow: never block on a modal dialog — most
                # often this just means a drive went offline mid-run.
                log.warning("Slideshow could not set wallpaper for %s: %s", path, exc)
                self._set_status(f"Skipped (unavailable): {Path(path).name}")
                self._refresh_source_menu()
            else:
                messagebox.showerror(APP_NAME, f"Could not set wallpaper:\n{exc}")
            return False

    def _record_history(self, path: str) -> None:
        """Append a successfully-applied path to the history ring (no-op if
        it's already the most recent entry) and persist it immediately."""
        if not self._history or self._history[-1] != path:
            self._history.append(path)
            save_history(self._history)

    def _set_wallpaper(self, silent: bool = False) -> None:
        if not (0 <= self.index < len(self.images)):
            self._set_status("Nothing selected.")
            return
        path = self.images[self.index]
        if self._apply_path(path, silent):
            self._record_history(path)

    def _history_back(self) -> None:
        """Step backward through the applied-wallpaper history. This is
        what tray Previous and Undo both do: 'previous' means the wallpaper
        actually shown before this one, not a deck-rewind — shuffle order
        isn't linear, so decrementing the index wouldn't retrace it."""
        if len(self._history) < 2:
            self._set_status("Nothing to undo.")
            return
        target = self._history[-2]
        if self._apply_path(target, silent=True):
            self._history.pop()
            if target in self.images:
                self.index = self.images.index(target)
                self._show_current()
            save_history(self._history)

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

    def _next_solar_trigger(self, now: datetime) -> Optional[datetime]:
        """Next dawn/sunrise/sunset/dusk boundary, using real sun-position
        math when a location is set and the sun actually crosses the
        relevant altitudes today; otherwise the four fallback_times via the
        same DST-safe helper daily mode uses, so an unset location or a
        polar date both degrade to something sane instead of stalling."""
        solar_cfg = self.cfg.get("solar", {})
        lat, lon = solar_cfg.get("latitude"), solar_cfg.get("longitude")
        if solar_cfg.get("enabled") and lat is not None and lon is not None:
            boundary = schedule.next_boundary(lat, lon, now)
            if boundary is not None:
                return boundary
        return next_daily_trigger(now, solar_cfg.get("fallback_times", []))

    def _solar_phase_now(self, now: datetime) -> str:
        solar_cfg = self.cfg.get("solar", {})
        lat, lon = solar_cfg.get("latitude"), solar_cfg.get("longitude")
        fallback_times = solar_cfg.get("fallback_times", [])
        if solar_cfg.get("enabled") and lat is not None and lon is not None:
            return schedule.current_phase(lat, lon, now, fallback_times)
        return schedule.phase_from_fallback(now, fallback_times)

    def _solar_advance(self) -> str:
        """Pick the next image for a solar-mode boundary tick: prefer
        images tagged for the current phase (dawn/day/dusk/night and their
        aliases), falling back to the full source — with an honest status
        line — when nothing in the library is tagged for that phase, so a
        library with no solar tags never stalls (notes_005 §2.2.1)."""
        phase = self._solar_phase_now(datetime.now())
        eligible = [
            i for i, path in enumerate(self.images)
            if schedule.phase_tag_matches(phase, get_tags(self.cfg, path))
        ]
        filtered = bool(eligible)
        if not eligible:
            eligible = list(range(len(self.images)))
        if self.shuffle_var.get() and len(eligible) > 1:
            choices = [i for i in eligible if i != self.index] or eligible
            self.index = random.choice(choices)
        else:
            later = [i for i in eligible if i > self.index]
            self.index = later[0] if later else eligible[0]
        self._show_current()
        suffix = "" if filtered else f" (unfiltered — no #{phase} tags)"
        return f"Slideshow · {phase}{suffix}"

    def _compute_next_due(self) -> None:
        """Set the wall-clock or monotonic time the next slideshow advance
        is due, from *now*. Recomputed fresh on every call (start, manual
        nav reset, resume-from-pause) rather than cached — same
        self-correcting behaviour v1.4 established for daily mode, now also
        how interval mode tolerates clock/monotonic-base changes."""
        mode = self.cfg["schedule"]["mode"]
        if mode == "daily":
            trigger = next_daily_trigger(datetime.now(), self.cfg["schedule"]["daily_times"])
            if trigger is not None:
                self._next_due_wall = trigger
                self._next_due_mono = None
                return
            # No valid daily times configured — fall back to the fixed
            # interval so the slideshow doesn't silently stall forever.
        elif mode == "solar":
            trigger = self._next_solar_trigger(datetime.now())
            if trigger is not None:
                self._next_due_wall = trigger
                self._next_due_mono = None
                return
            # Solar math unavailable and no fallback times either — same
            # last-resort as daily mode above.
        seconds = resolve_interval_seconds(
            self.interval_var.get(), self.cfg.get("interval_custom_seconds")
        )
        self._next_due_mono = time.monotonic() + seconds
        self._next_due_wall = None

    def _schedule_next(self) -> None:
        if not self.images:
            self._stop_slideshow()
            return
        self._compute_next_due()
        if self._slideshow_job is None:
            self._slideshow_job = self.after(SCHEDULER_TICK_MS, self._scheduler_heartbeat)

    def _scheduler_heartbeat(self) -> None:
        """1 Hz poll: is the armed due-time in the past? A single long
        after(seconds * 1000) would either overflow Tk's millisecond arg for
        very long intervals or, worse, behave unpredictably across a
        sleep/hibernate gap; polling a due-time instead means at most one
        tick fires no matter how long the gap was — never a catch-up burst."""
        self._slideshow_job = None
        if not self._slideshow_running or self._auto_pause_reasons or not self.images:
            return  # _power_monitor_tick / _schedule_next re-arm when appropriate
        due = (
            datetime.now() >= self._next_due_wall
            if self._next_due_wall is not None
            else self._next_due_mono is not None and time.monotonic() >= self._next_due_mono
        )
        if due:
            self._slideshow_tick()
        else:
            self._slideshow_job = self.after(SCHEDULER_TICK_MS, self._scheduler_heartbeat)

    def _slideshow_tick(self) -> None:
        if not self.images:
            self._stop_slideshow()
            return
        # Advance without treating this as manual nav (avoids timer reset races).
        solar_status = None
        if self.cfg["schedule"]["mode"] == "solar":
            solar_status = self._solar_advance()
        elif self.shuffle_var.get():
            self._advance_shuffle()
        else:
            self.index = (self.index + 1) % len(self.images)
            self._show_current()
        self._set_wallpaper(silent=True)
        if solar_status:
            self._set_status(solar_status)
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
        self._next_due_mono = None
        self._next_due_wall = None
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
            pystray.MenuItem("Undo Last Applied", self._on_tray_undo),
            pystray.MenuItem(
                "Pause Slideshow" if slideshow_running else "Resume Slideshow",
                self._on_tray_toggle_slideshow,
            ),
            pystray.MenuItem("Reveal in Explorer", self._on_tray_reveal),
            pystray.MenuItem("About Desktop Vista…", self._on_tray_about),
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
        # "Previous" walks applied history, not the deck — see _history_back.
        self.after(0, self._history_back)

    def _on_tray_undo(self, _icon=None, _item=None) -> None:
        self.after(0, self._history_back)

    def _tray_navigate_and_apply(self, delta: int) -> None:
        """Tray "Next Wallpaper" must change the desktop, not just the
        in-window preview — the main window's arrow buttons keep the
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
        self._reveal_path_in_explorer(self.images[self.index])

    def _on_tray_about(self, _icon=None, _item=None) -> None:
        self.after(0, self._show_about)

    def _show_about(self) -> None:
        """Tray and in-window About share one entry point and one copy
        source (ABOUT_COPY) — the Settings page already has the block,
        so this just surfaces it rather than opening a second window."""
        self._tray_restore()
        self._show_page("settings")

    def _on_tray_exit(self, _icon=None, _item=None) -> None:
        self.after(0, self._on_close)

    # ---------------- CLI / scripting IPC ----------------

    def _start_ipc_server(self) -> None:
        if not ipc.is_available():
            return
        try:
            self._ipc_server = ipc.IpcServer(self._handle_ipc_command, lambda fn: self.after(0, fn))
            self._ipc_server.start()
        except Exception as exc:
            log.warning("IPC server unavailable: %s", exc)
            self._ipc_server = None

    def _stop_ipc_server(self) -> None:
        if self._ipc_server is not None:
            try:
                self._ipc_server.stop()
            except Exception:
                pass
            self._ipc_server = None

    def _handle_ipc_command(self, payload: dict) -> dict:
        """Runs on the Tk thread (marshalled by ipc.IpcServer via after(0, ...))
        — safe to touch widgets/self.cfg directly, same as any other handler."""
        cmd = payload.get("cmd")
        if cmd == "ping":
            return {"ok": True}
        if cmd == "status":
            return {
                "ok": True,
                "version": APP_VERSION,
                "running": self._slideshow_running,
                "paused": sorted(self._auto_pause_reasons),
                "current": self.images[self.index] if 0 <= self.index < len(self.images) else None,
                "source": {"kind": self._active_kind, "id": self._active_id},
            }
        if cmd == "show":
            self._tray_restore()
            return {"ok": True}
        try:
            if cmd == "next":
                self._step(1)
                self._set_wallpaper(silent=True)
            elif cmd in ("prev", "undo"):
                self._history_back()
            elif cmd == "pause":
                if self._slideshow_running:
                    self._stop_slideshow()
            elif cmd == "resume":
                if not self._slideshow_running:
                    self._start_slideshow()
            elif cmd == "toggle":
                self._toggle_slideshow()
            elif cmd == "favourite":
                self._toggle_favourite()
            elif cmd == "hide":
                self._hide_current()
            elif cmd == "set":
                path = payload.get("path")
                if not isinstance(path, str) or not path:
                    return {"ok": False, "error": "missing 'path'"}
                if not self._apply_path(path, silent=True):
                    return {"ok": False, "error": f"could not apply {path}"}
                self._record_history(path)
                if path in self.images:
                    self.index = self.images.index(path)
                    self._show_current()
            else:
                return {"ok": False, "error": f"unknown command: {cmd!r}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "applied": self.images[self.index] if 0 <= self.index < len(self.images) else None,
        }

    # ---------------- Global hotkeys ----------------

    def _start_hotkeys(self) -> None:
        if not hotkeys.is_available() or not self.cfg.get("hotkeys", {}).get("enabled", True):
            self._set_hotkey_status_text(enabled=False)
            return
        bindings: list[tuple[int, int, int]] = []
        for action in HOTKEY_ACTIONS:
            parsed = hotkeys.parse_binding(self.cfg["hotkeys"][action])
            if parsed is not None:
                mods, vk = parsed
                bindings.append((HOTKEY_ACTION_IDS[action], mods, vk))
        if not bindings:
            self._set_hotkey_status_text(enabled=False)
            return
        try:
            self._hotkey_listener = hotkeys.HotkeyListener(
                bindings, on_hotkey=lambda hid: self.after(0, self._on_hotkey_fired, hid)
            )
            self._hotkey_listener.start()
        except Exception as exc:
            log.warning("Global hotkeys unavailable: %s", exc)
            self._hotkey_listener = None
            self._set_hotkey_status_text(enabled=False)
            return
        # RegisterHotKey is effectively instant; a short bounded wait here
        # (once, at startup) lets a conflict be reported immediately rather
        # than silently, without risking an indefinite UI freeze.
        self._hotkey_listener.ready.wait(timeout=1.0)
        if self._hotkey_listener.conflicts:
            conflicts = ", ".join(self._hotkey_listener.conflicts)
            log.warning("Hotkey binding conflict (already in use elsewhere): %s", conflicts)
        self._set_hotkey_status_text(enabled=True)

    def _stop_hotkeys(self) -> None:
        if self._hotkey_listener is not None:
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass
            self._hotkey_listener = None

    def _set_hotkey_status_text(self, enabled: bool) -> None:
        label = getattr(self, "hotkeys_status_label", None)
        if label is None:
            return
        if not enabled:
            label.configure(text="Hotkeys unavailable or disabled.")
            return
        conflicts = self._hotkey_listener.conflicts if self._hotkey_listener else []
        lines = [
            f"{action}: {self.cfg['hotkeys'][action]}"
            + (" (conflict)" if hotkeys.format_binding(*hotkeys.parse_binding(self.cfg["hotkeys"][action])) in conflicts else "")
            for action in HOTKEY_ACTIONS
        ]
        label.configure(text="  ·  ".join(lines))

    def _on_hotkey_fired(self, hotkey_id: int) -> None:
        action = next((a for a, i in HOTKEY_ACTION_IDS.items() if i == hotkey_id), None)
        if action is not None:
            self._handle_ipc_command({"cmd": action})

    def _on_hotkeys_enabled_changed(self) -> None:
        self.cfg["hotkeys"]["enabled"] = bool(self.hotkeys_enabled_var.get())
        self._flush_save()
        self._stop_hotkeys()
        self._start_hotkeys()

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
        self._stop_ipc_server()
        self._stop_hotkeys()
        ipc.release_primary(self._mutex_handle)
        self._mutex_handle = None
        self._close_inspection_mode()
        # Both own periodic after() jobs; their own destroy() cancels those
        # before the parent's own teardown proceeds (notes_006 §4: "no
        # bind_all or global unbind is used", timer cleanup owned locally).
        for component in (getattr(self, "hud", None), getattr(self, "toasts", None)):
            if component is not None:
                try:
                    component.destroy()
                except Exception:
                    pass
        if self._com_backend is not None:
            try:
                self._com_backend.close()
            except Exception:
                pass
        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            # Python < 3.9 cancel_futures not available
            self._executor.shutdown(wait=False)
        self.destroy()


def run_selftest() -> int:
    """
    Print diagnostic info about the optional Windows integrations and exit
    without opening a window. Mainly for confirming a packaged build
    bundled everything correctly (e.g. after changing build_exe.spec).
    """
    print(f"Desktop Vista {APP_VERSION}  (frozen={FROZEN}, platform={sys.platform})")
    print(f"winreg available:   {winreg is not None}")
    print(f"pystray available:  {pystray is not None}")
    print(f"COM backend module: {windows_wallpaper_com is not None}")
    win32_monitors = enumerate_monitors()
    print(f"Win32 monitor enumeration: {len(win32_monitors)} monitor(s) -> {win32_monitors}")
    monitor_dpi = enumerate_monitor_dpi()
    print(f"Per-monitor DPI (GetDpiForMonitor): {monitor_dpi}")
    print(f"High contrast active (SPI_GETHIGHCONTRAST): {is_high_contrast_active()}")
    try:
        probe_root = ctk.CTk()
        probe_root.withdraw()
        tk_scaling = probe_root.tk.call("tk", "scaling")
        probe_root.destroy()
        print(f"Tk scaling factor: {tk_scaling}")
    except Exception as exc:
        print(f"Tk scaling factor: unavailable ({exc})")

    # v1.6 — single-instance mutex, named-pipe IPC, global hotkeys, solar math.
    print(f"ipc available:      {ipc.is_available()}")
    if ipc.is_available():
        mutex_handle, is_primary = ipc.try_become_primary()
        print(f"mutex acquire: is_primary={is_primary}"
              + ("" if is_primary else " (another instance is already running)"))
        if is_primary:
            server = ipc.IpcServer(lambda payload: {"ok": True, "echo": payload}, lambda fn: fn())
            server.start()
            try:
                time.sleep(0.2)  # let the server's first CreateNamedPipeW/ConnectNamedPipe settle
                reply = ipc.send_command({"cmd": "ping"}, timeout=2.0)
                print(f"named-pipe round trip: {reply}")
            except Exception as exc:
                print(f"named-pipe round trip FAILED: {exc}")
            finally:
                server.stop()
                server.join(timeout=2.0)
        ipc.release_primary(mutex_handle)

    print(f"hotkeys available:  {hotkeys.is_available()}")
    default_bindings = {k: v for k, v in DEFAULT_CONFIG["hotkeys"].items() if k != "enabled"}
    parsed_ok = all(hotkeys.parse_binding(b) is not None for b in default_bindings.values())
    print(f"default hotkey bindings parse OK: {parsed_ok} {default_bindings}")

    solar_events = schedule.solar_phase_boundaries(51.5074, -0.1278, datetime(2026, 6, 21, 12, 0))
    print(f"solar calc (London, 2026-06-21 fixture): {sorted(solar_events.keys())}")

    if windows_wallpaper_com is None:
        return 0
    try:
        backend = windows_wallpaper_com.ComWallpaperBackend()
        try:
            com_monitors = backend.enumerate_monitors()
            print(f"COM monitor enumeration:   {len(com_monitors)} monitor(s) -> {com_monitors}")
        finally:
            backend.close()
    except Exception as exc:
        print(f"COM monitor enumeration FAILED: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(run_selftest())
    if sys.platform != "win32":
        print("Desktop Vista is designed for Windows.")

    _argv = sys.argv[1:]
    _mutex_handle, _is_primary = ipc.try_become_primary()

    if not _is_primary:
        # Another instance already owns the mutex — never open a second
        # Tk window (notes_005 §2.6: two instances would both apply
        # wallpapers and race save_config). Forward any recognised CLI
        # command to it over the named pipe instead, and exit.
        _payload = ipc.cli_payload(_argv) or {"cmd": "show"}
        try:
            _reply = ipc.send_command(_payload)
        except OSError as exc:
            print(f"Could not reach the running {APP_NAME} instance: {exc}")
            sys.exit(1)
        print(json.dumps(_reply))
        sys.exit(0 if _reply.get("ok") else 1)

    start_minimized = "--minimized" in _argv
    DesktopVista(start_minimized=start_minimized, mutex_handle=_mutex_handle).mainloop()
