# Copyright (c) 2026 hawkers63. All Rights Reserved.
#
# Desktop Vista is proprietary software. Unauthorised copying, reproduction,
# redistribution, modification, reverse-engineering, or commercial use of this
# file or any portion of it is strictly prohibited without prior written consent
# from the copyright holder (hawkers63).
#
# See the LICENSE file in the project root for the full proprietary notice.
"""
Desktop Vista  —  All my drives. One perfect view.
Version 1.1 hardened  (September 2026)

A lightweight Windows wallpaper manager.

Location : D:\\Desktop_Vista\\desktop_vista.py
Config   : D:\\Desktop_Vista\\config.json  (created automatically)

Requirements (run once):
    pip install customtkinter pillow

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

Planned for v2: minimise to system tray (pystray), multi-monitor.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
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

import customtkinter as ctk
from PIL import Image, ImageOps
from tkinter import filedialog, messagebox

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
TAGLINE = "All my drives. One perfect view."
APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"

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
}


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


def _validate_config(raw: dict) -> dict[str, Any]:
    """Coerce *raw* into a valid config dict, filling defaults where needed."""
    cfg = dict(DEFAULT_CONFIG)

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
    if isinstance(interval, str) and interval in SLIDESHOW_INTERVALS:
        cfg["interval"] = interval
    else:
        log.warning("Invalid 'interval' in config; using default.")

    shuffle = raw.get("shuffle", DEFAULT_CONFIG["shuffle"])
    if isinstance(shuffle, bool):
        cfg["shuffle"] = shuffle
    else:
        log.warning("Invalid 'shuffle' in config; using default.")

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
    """Atomically write *cfg* to *path* via a temporary sibling file."""
    cfg_path = path if path is not None else CONFIG_PATH
    tmp_path = cfg_path.with_suffix(cfg_path.suffix + ".tmp")
    try:
        data = json.dumps(cfg, indent=2)
        tmp_path.write_text(data, encoding="utf-8")
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


def _load_preview_image(path: str, max_w: int, max_h: int) -> tuple[Image.Image, int, int]:
    """Open *path*, apply EXIF transpose, thumbnail to max box. Returns (rgb, w, h)."""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        width, height = im.size
        im.draft("RGB", (max_w, max_h))
        im = im.convert("RGB")
        im.thumbnail((max_w, max_h), Image.LANCZOS)
        # Copy pixels out of the context manager
        out = im.copy()
    return out, width, height


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class DesktopVista(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME}  —  {TAGLINE}")
        self.geometry("1180x620")
        self.minsize(980, 560)

        self.cfg = load_config()
        self.images: list[str] = []
        self.index: int = -1
        self._preview_ref = None  # keep CTkImage alive
        self._slideshow_job: Any = None
        self._save_job: Any = None
        self._shuffle_order: list[int] = []
        self._load_token: int = 0
        self._preview_size: tuple[int, int] = (PREVIEW_W, PREVIEW_H)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dv-img")
        self._closing = False

        self._build_ui()
        self._restore_state()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------- UI construction ----------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---- Left sidebar: control panel ----
        side = ctk.CTkFrame(self, width=300, corner_radius=12)
        side.grid(row=0, column=0, sticky="nsw", padx=(12, 6), pady=12)
        side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(side, text=APP_NAME, font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(16, 0), sticky="w")
        ctk.CTkLabel(side, text=TAGLINE, font=ctk.CTkFont(size=12), text_color="gray70").grid(
            row=1, column=0, padx=16, pady=(0, 14), sticky="w")

        # Folders
        ctk.CTkLabel(side, text="WALLPAPER FOLDERS", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray60").grid(row=2, column=0, padx=16, sticky="w")
        self.folder_var = ctk.StringVar(value="(no folders yet)")
        self.folder_menu = ctk.CTkOptionMenu(
            side, variable=self.folder_var, values=["(no folders yet)"],
            command=self._on_folder_selected, dynamic_resizing=False)
        self.folder_menu.grid(row=3, column=0, padx=16, pady=(4, 6), sticky="ew")

        fbtns = ctk.CTkFrame(side, fg_color="transparent")
        fbtns.grid(row=4, column=0, padx=16, sticky="ew")
        fbtns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(fbtns, text="+ Add folder", command=self._add_folder).grid(
            row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(fbtns, text="Remove", fg_color="gray30", hover_color="gray25",
                      command=self._remove_folder).grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # Fit style
        ctk.CTkLabel(side, text="FIT STYLE", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray60").grid(row=5, column=0, padx=16, pady=(18, 0), sticky="w")
        self.style_var = ctk.StringVar(value=self.cfg["style"])
        ctk.CTkOptionMenu(side, variable=self.style_var, values=list(WALLPAPER_STYLES),
                          command=self._on_style_changed).grid(
            row=6, column=0, padx=16, pady=(4, 0), sticky="ew")

        # Primary action
        self.set_btn = ctk.CTkButton(
            side, text="Set as Wallpaper", height=44,
            font=ctk.CTkFont(size=15, weight="bold"), command=self._set_wallpaper)
        self.set_btn.grid(row=7, column=0, padx=16, pady=(22, 0), sticky="ew")

        # Slideshow
        ctk.CTkLabel(side, text="SLIDESHOW", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray60").grid(row=8, column=0, padx=16, pady=(24, 0), sticky="w")
        self.interval_var = ctk.StringVar(value=self.cfg["interval"])
        ctk.CTkOptionMenu(side, variable=self.interval_var, values=list(SLIDESHOW_INTERVALS),
                          command=self._on_interval_changed).grid(
            row=9, column=0, padx=16, pady=(4, 6), sticky="ew")
        self.shuffle_var = ctk.BooleanVar(value=self.cfg["shuffle"])
        ctk.CTkSwitch(side, text="Shuffle", variable=self.shuffle_var,
                      command=self._on_shuffle_changed).grid(row=10, column=0, padx=16, sticky="w")
        self.slide_btn = ctk.CTkButton(
            side, text="Start Slideshow", height=40, fg_color="#2e7d32", hover_color="#27682a",
            command=self._toggle_slideshow)
        self.slide_btn.grid(row=11, column=0, padx=16, pady=(12, 0), sticky="ew")

        # Status
        side.grid_rowconfigure(12, weight=1)
        self.status = ctk.CTkLabel(side, text="Ready.", text_color="gray60",
                                   font=ctk.CTkFont(size=11), wraplength=260, justify="left")
        self.status.grid(row=13, column=0, padx=16, pady=(0, 14), sticky="sw")

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
        nav.grid(row=2, column=0, pady=(8, 16))
        ctk.CTkButton(nav, text="◀  Previous", width=130, command=self._prev).grid(row=0, column=0, padx=6)
        ctk.CTkButton(nav, text="Random", width=110, fg_color="gray30", hover_color="gray25",
                      command=self._random).grid(row=0, column=1, padx=6)
        ctk.CTkButton(nav, text="Next  ▶", width=130, command=self._next).grid(row=0, column=2, padx=6)

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

        # Dynamic 16:9 preview sizing
        self.preview.bind("<Configure>", self._on_preview_configure)
        self.main.bind("<Configure>", self._on_preview_configure)

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

    def _restore_state(self) -> None:
        """Load folder without showing, then restore last image and show once."""
        self._refresh_folder_menu()
        folder = self.cfg.get("current_folder")
        if folder and folder in self.cfg["folders"]:
            self._load_folder(folder, show=False)
            last = self.cfg.get("current_image")
            if last in self.images:
                self.index = self.images.index(last)
            elif self.images:
                self.index = 0
            if self.images:
                self._show_current()
            else:
                self._flush_save()
        elif self.cfg["folders"]:
            self._load_folder(self.cfg["folders"][0], show=True)

    # ---------------- Folders ----------------

    def _refresh_folder_menu(self) -> None:
        folders = self.cfg["folders"]
        if folders:
            self.folder_menu.configure(values=folders)
            if self.folder_var.get() not in folders:
                self.folder_var.set(folders[0])
        else:
            self.folder_menu.configure(values=["(no folders yet)"])
            self.folder_var.set("(no folders yet)")

    def _add_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Choose a wallpaper folder")
        if not chosen:
            return
        chosen = os.path.normpath(chosen)
        if chosen not in self.cfg["folders"]:
            self.cfg["folders"].append(chosen)
        self.folder_var.set(chosen)
        self._refresh_folder_menu()
        self._load_folder(chosen)

    def _remove_folder(self) -> None:
        folder = self.folder_var.get()
        if folder not in self.cfg["folders"]:
            return
        if not messagebox.askyesno(
            APP_NAME,
            f"Remove this folder from Desktop Vista?\n\n{folder}\n\n(No files are deleted.)",
        ):
            return
        self._stop_slideshow()
        self.cfg["folders"].remove(folder)
        self._refresh_folder_menu()
        if self.cfg["folders"]:
            self._load_folder(self.cfg["folders"][0])
        else:
            self.images, self.index = [], -1
            self._shuffle_order = []
            self.cfg["current_folder"] = None
            self.cfg["current_image"] = None
            self.preview.configure(image=None, text="Add a folder to begin")
            self.meta.configure(text="")
            self._flush_save()

    def _on_folder_selected(self, folder: str) -> None:
        if folder in self.cfg["folders"]:
            self._load_folder(folder)

    def _load_folder(self, folder: str, show: bool = True) -> None:
        self._flush_save()  # persist previous folder/image before switching
        self.cfg["current_folder"] = folder
        self.folder_var.set(folder)
        self.images = list_images(folder)
        self._shuffle_order = []
        if not self.images:
            self.index = -1
            if show:
                self.preview.configure(image=None, text="No images found in this folder")
                self.meta.configure(text="")
            # Distinguish empty vs unreadable: if path missing/unreadable, list_images
            # already returned []. Surface a clear status either way.
            try:
                readable = Path(folder).is_dir()
            except OSError:
                readable = False
            if not readable:
                self._set_status("Folder is empty or unreadable.")
            else:
                self._set_status("No images found in this folder.")
            self._flush_save()
            if self._slideshow_job is not None:
                self._stop_slideshow()
            return

        self.index = 0
        self._set_status(f"{len(self.images)} images in {Path(folder).name or folder}")
        if show:
            self._show_current()
        else:
            self._flush_save()

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
        if not (0 <= self.index < len(self.images)):
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
                self.after(0, lambda: self._on_preview_error(token, path, exc))
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
        if not self._shuffle_order:
            self._shuffle_order = build_shuffle_deck(len(self.images), self.index)
        if self._shuffle_order:
            self.index = self._shuffle_order.pop(0)
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
        self._save()

    def _set_wallpaper(self) -> None:
        if not (0 <= self.index < len(self.images)):
            self._set_status("Nothing selected.")
            return
        path = self.images[self.index]
        try:
            set_windows_wallpaper(path, self.style_var.get())
            self._set_status(f"Wallpaper set: {Path(path).name}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not set wallpaper:\n{exc}")

    # ---------------- Slideshow ----------------

    def _on_interval_changed(self, _value: str) -> None:
        self._flush_save()
        if self._slideshow_job is not None:
            self._stop_slideshow(update_status=False)
            self._start_slideshow()

    def _toggle_slideshow(self) -> None:
        if self._slideshow_job is None:
            self._start_slideshow()
        else:
            self._stop_slideshow()

    def _start_slideshow(self) -> None:
        if not self.images:
            self._set_status("Add a folder with images first.")
            return
        self.slide_btn.configure(text="Stop Slideshow", fg_color="#b71c1c", hover_color="#951616")
        self._set_status(f"Slideshow running — every {self.interval_var.get()}.")
        self._set_wallpaper()
        self._schedule_next()

    def _schedule_next(self) -> None:
        if not self.images:
            self._stop_slideshow()
            return
        interval_key = self.interval_var.get()
        seconds = SLIDESHOW_INTERVALS.get(interval_key, 900)
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
        self._set_wallpaper()
        if self.images:
            self._schedule_next()
        else:
            self._stop_slideshow()

    def _stop_slideshow(self, update_status: bool = True) -> None:
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

    # ---------------- Close ----------------

    def _cancel_after_jobs(self) -> None:
        for attr in ("_slideshow_job", "_save_job"):
            job = getattr(self, attr, None)
            if job is not None:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
                setattr(self, attr, None)

    def _on_close(self) -> None:
        self._closing = True
        self._load_token += 1  # invalidate in-flight preview loads
        self._cancel_after_jobs()
        self._write_config()
        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            # Python < 3.9 cancel_futures not available
            self._executor.shutdown(wait=False)
        self.destroy()


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Desktop Vista is designed for Windows.")
    DesktopVista().mainloop()
