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
Version 1.0  (September 2026)

A lightweight Windows wallpaper manager.

Location : D:\\Desktop_Vista\\desktop_vista.py
Config   : D:\\Desktop_Vista\\config.json  (created automatically)

Requirements (run once):
    pip install customtkinter pillow

Features in v1:
    - Manage any number of wallpaper folders across any drives
    - Fast 16:9 preview (decoded straight to preview size, not full 4K)
    - Previous / Next / Random navigation
    - Set as Wallpaper with Fill / Fit / Stretch / Centre / Span style
    - Folder slideshow with interval and shuffle
    - Remembers folders, style, interval, shuffle and last image

Planned for v2: minimise to system tray (pystray), multi-monitor.
"""

import ctypes
import json
import os
import random
import sys
import winreg
from pathlib import Path

import customtkinter as ctk
from PIL import Image
from tkinter import filedialog, messagebox

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

APP_NAME = "Desktop Vista"
TAGLINE = "All my drives. One perfect view."
APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

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

PREVIEW_W, PREVIEW_H = 800, 450  # 16:9

DEFAULT_CONFIG = {
    "folders": [],
    "current_folder": None,
    "current_image": None,
    "style": "Fill",
    "interval": "15 minutes",
    "shuffle": False,
}


# ---------------------------------------------------------------------------
# Windows helpers
# ---------------------------------------------------------------------------

def set_windows_wallpaper(path: str, style: str) -> None:
    """Apply a wallpaper and its fit style. Windows only."""
    if sys.platform != "win32":
        raise RuntimeError("Desktop Vista only sets wallpapers on Windows.")

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
        SPI_SETDESKWALLPAPER, 0, path, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    )
    if not ok:
        raise ctypes.WinError()


def human_size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def list_images(folder: str) -> list[str]:
    try:
        return sorted(
            str(p) for p in Path(folder).iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        )
    except (FileNotFoundError, PermissionError):
        return []


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"Could not save config: {exc}")


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
        self._preview_ref = None       # keep CTkImage alive
        self._slideshow_job = None     # id from self.after()

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
                          command=lambda _: self._save()).grid(
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
                      command=self._save).grid(row=10, column=0, padx=16, sticky="w")
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
        main = ctk.CTkFrame(self, corner_radius=12)
        main.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(0, weight=1)

        self.preview = ctk.CTkLabel(main, text="Add a folder to begin", text_color="gray50",
                                    font=ctk.CTkFont(size=16))
        self.preview.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="nsew")

        self.meta = ctk.CTkLabel(main, text="", text_color="gray60", font=ctk.CTkFont(size=12))
        self.meta.grid(row=1, column=0, padx=16, sticky="ew")

        nav = ctk.CTkFrame(main, fg_color="transparent")
        nav.grid(row=2, column=0, pady=(8, 16))
        ctk.CTkButton(nav, text="◀  Previous", width=130, command=self._prev).grid(row=0, column=0, padx=6)
        ctk.CTkButton(nav, text="Random", width=110, fg_color="gray30", hover_color="gray25",
                      command=self._random).grid(row=0, column=1, padx=6)
        ctk.CTkButton(nav, text="Next  ▶", width=130, command=self._next).grid(row=0, column=2, padx=6)

        # Keyboard shortcuts
        self.bind("<Left>", lambda e: self._prev())
        self.bind("<Right>", lambda e: self._next())
        self.bind("<Return>", lambda e: self._set_wallpaper())
        self.bind("r", lambda e: self._random())

    # ---------------- State ----------------

    def _restore_state(self) -> None:
        self._refresh_folder_menu()
        folder = self.cfg.get("current_folder")
        if folder and folder in self.cfg["folders"]:
            self._load_folder(folder)
            last = self.cfg.get("current_image")
            if last in self.images:
                self.index = self.images.index(last)
                self._show_current()
        elif self.cfg["folders"]:
            self._load_folder(self.cfg["folders"][0])

    def _save(self, *_args) -> None:
        self.cfg["style"] = self.style_var.get()
        self.cfg["interval"] = self.interval_var.get()
        self.cfg["shuffle"] = self.shuffle_var.get()
        self.cfg["current_image"] = self.images[self.index] if 0 <= self.index < len(self.images) else None
        save_config(self.cfg)

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)

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
        if not messagebox.askyesno(APP_NAME, f"Remove this folder from Desktop Vista?\n\n{folder}\n\n(No files are deleted.)"):
            return
        self._stop_slideshow()
        self.cfg["folders"].remove(folder)
        self._refresh_folder_menu()
        if self.cfg["folders"]:
            self._load_folder(self.cfg["folders"][0])
        else:
            self.images, self.index = [], -1
            self.cfg["current_folder"] = None
            self.preview.configure(image=None, text="Add a folder to begin")
            self.meta.configure(text="")
            self._save()

    def _on_folder_selected(self, folder: str) -> None:
        if folder in self.cfg["folders"]:
            self._load_folder(folder)

    def _load_folder(self, folder: str) -> None:
        self.cfg["current_folder"] = folder
        self.folder_var.set(folder)
        self.images = list_images(folder)
        if self.images:
            self.index = 0
            self._set_status(f"{len(self.images)} images in {Path(folder).name or folder}")
            self._show_current()
        else:
            self.index = -1
            self.preview.configure(image=None, text="No images found in this folder")
            self.meta.configure(text="")
            self._set_status("Folder is empty or unreadable.")
            self._save()

    # ---------------- Preview & navigation ----------------

    def _show_current(self) -> None:
        if not (0 <= self.index < len(self.images)):
            return
        path = self.images[self.index]
        try:
            with Image.open(path) as im:
                width, height = im.size
                # Decode straight to something near preview size — cheap for JPEGs.
                im.draft("RGB", (PREVIEW_W, PREVIEW_H))
                im = im.convert("RGB")
                im.thumbnail((PREVIEW_W, PREVIEW_H), Image.LANCZOS)
                self._preview_ref = ctk.CTkImage(light_image=im, dark_image=im, size=im.size)
        except Exception as exc:  # corrupt or unsupported file
            self.preview.configure(image=None, text=f"Cannot open image\n{Path(path).name}")
            self.meta.configure(text=str(exc))
            return

        self.preview.configure(image=self._preview_ref, text="")
        size = human_size(os.path.getsize(path))
        self.meta.configure(
            text=f"{Path(path).name}    •    {width} × {height}    •    {size}    "
                 f"•    {self.index + 1} of {len(self.images)}")
        self._save()

    def _step(self, delta: int) -> None:
        if not self.images:
            return
        self.index = (self.index + delta) % len(self.images)
        self._show_current()

    def _prev(self) -> None:
        self._step(-1)

    def _next(self) -> None:
        self._step(1)

    def _random(self) -> None:
        if len(self.images) > 1:
            choices = [i for i in range(len(self.images)) if i != self.index]
            self.index = random.choice(choices)
            self._show_current()

    # ---------------- Wallpaper ----------------

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
        self._save()
        if self._slideshow_job is not None:      # restart with the new interval
            self._stop_slideshow()
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
        seconds = SLIDESHOW_INTERVALS[self.interval_var.get()]
        self._slideshow_job = self.after(seconds * 1000, self._slideshow_tick)

    def _slideshow_tick(self) -> None:
        if self.shuffle_var.get():
            self._random()
        else:
            self._next()
        self._set_wallpaper()
        self._schedule_next()

    def _stop_slideshow(self) -> None:
        if self._slideshow_job is not None:
            self.after_cancel(self._slideshow_job)
            self._slideshow_job = None
        self.slide_btn.configure(text="Start Slideshow", fg_color="#2e7d32", hover_color="#27682a")
        self._set_status("Slideshow stopped.")

    # ---------------- Close ----------------

    def _on_close(self) -> None:
        self._save()
        self.destroy()


if __name__ == "__main__":
    if sys.platform != "win32":
        print("Desktop Vista is designed for Windows.")
    DesktopVista().mainloop()
