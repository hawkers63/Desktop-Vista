# Desktop Vista

**All my drives. One perfect view.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows&logoColor=white)](https://github.com/hawkers63/Desktop-Vista)
[![CI](https://github.com/hawkers63/Desktop-Vista/actions/workflows/ci.yml/badge.svg)](https://github.com/hawkers63/Desktop-Vista/actions/workflows/ci.yml)
[![Licence](https://img.shields.io/badge/Licence-Proprietary%20%2F%20All%20Rights%20Reserved-red)](LICENSE)
[![Release](https://img.shields.io/github/v/release/hawkers63/Desktop-Vista)](https://github.com/hawkers63/Desktop-Vista/releases/latest)

A lightweight Windows wallpaper manager built with CustomTkinter. Desktop Vista gathers wallpaper folders from every local and external drive into one dual-pane workspace, and pairs that with a memory-efficient 16:9 preview engine so you can browse large (including 4K) images without decoding them at full resolution.

---

## Why Desktop Vista?

Windows Background settings become awkward when wallpapers live across several disks. Desktop Vista exists so you can:

- Keep every wallpaper folder — internal, USB, or network-mapped — in one control panel
- Preview candidates instantly in a fixed 16:9 frame (decoded straight to preview size)
- Apply a single image or run a folder slideshow without returning to the Control Panel

The dual-pane layout is intentional: a left **control panel** for folders, fit style, and slideshow; a right **canvas** for preview, metadata, and Previous / Random / Next navigation. Browse on the right; manage sources and timing on the left.

---

## Release

| | |
| --- | --- |
| **Current** | **[v1.8.1](https://github.com/hawkers63/Desktop-Vista/releases/tag/v1.8.1)** (2026-09-10) |
| **App version** | `APP_VERSION = "1.8"` in `desktop_vista.py` |
| **Highlights** | Hidden Items playback invariants; Hidden manager hygiene; reusable `EditorSheet`; About / copyright in Settings & tray; topology join labels; a11y prep (high-contrast, multi-DPI selftest). Walkthrough fixes: CustomTkinter appearance-mode crash rename, sidebar layout gap, tab-order/contrast pass |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) · [Releases](https://github.com/hawkers63/Desktop-Vista/releases) |
| **Recent tags** | [`v1.8.1`](https://github.com/hawkers63/Desktop-Vista/releases/tag/v1.8.1) · [`v1.7`](https://github.com/hawkers63/Desktop-Vista/releases/tag/v1.7) · [`v1.2`](https://github.com/hawkers63/Desktop-Vista/releases/tag/v1.2) |

**On `main` since v1.8.1:** multi-DPI scaling clip check closed (100/125/150/200% Pass); ROADMAP updates for proposed v1.9 Help & polish and deferred v2.0 (no dual-monitor hardware on actual-use machines). See **Unreleased** in the changelog.

> Maintainers: when cutting a release, bump `APP_VERSION`, update this **Release** table, add a CHANGELOG entry, tag (`vX.Y` / `vX.Y.Z`), and publish a GitHub Release so badges and links stay honest.

---

## Dual-pane workflow

1. **Add folders** in the left pane (any drive path your machine can read).
2. **Select a folder** to load its images into the preview canvas.
3. **Browse** with Previous / Random / Next (or the keyboard shortcuts below).
4. **Choose a fit style** (Fill, Fit, Stretch, Centre, Span) before applying.
5. **Set as Wallpaper** for the current image, or start a **slideshow** with your preferred interval and optional shuffle.

Preferences and the last-selected image are restored from `config.json` on the next launch.

---

## Preview engine

The preview pane keeps a fixed 16:9 aspect ratio. Pillow decodes images to preview size rather than loading full-resolution bitmaps into the UI, which keeps memory use low when you walk through large collections. Supported types: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`.

---

## Key features

- **Multi-drive folder management** — add or remove wallpaper directories from any drive
- **Instantaneous 16:9 preview decoding** — Pillow decodes to preview size for a fast, light UI
- **Custom slideshow intervals** — 1 minute through 1 day, or a "Custom…" interval in seconds
- **Shuffle engine** — optional random order during slideshows
- **Fit styles** — Fill, Fit, Stretch, Centre, Span (Windows wallpaper registry styles)
- **Keyboard navigation** — browse and apply without reaching for the mouse
- **Persistent preferences** — folders, style, interval, shuffle, and last image remembered in `config.json`
- **System tray** — closing the window hides Desktop Vista to the tray instead of quitting; the tray menu shows the current image and offers Next / Previous, Pause / Resume slideshow, Reveal in Explorer, Open Desktop Vista, and Exit
- **Start with Windows** — an optional Run-key entry launches Desktop Vista minimised to the tray at login (`--minimized` flag)
- **Offline-aware folders** — folders on a disconnected drive show `(offline)` in the folder dropdown, and an unattended slideshow skips missing files instead of stopping on an error dialog
- **Branded icon** — the window and tray icon use the Desktop Vista glyph (`icon/desktop_vista.ico`), with a procedural fallback if the asset is ever missing
- **Tray Next/Previous apply the wallpaper** — not just the in-window preview, so the tray menu does what its labels say
- **Playlists** — group folders from any drives into one named, deduplicated slideshow source
- **Favourites & Hide** — non-destructive per-image curation; hidden images are filtered out of playback everywhere without touching the source file
- **Drive reconnect watcher** — offline badges and empty sources refresh automatically on a 15-second poll
- **Battery Saver & fullscreen auto-pause** — the slideshow pauses itself on Battery Saver or while a fullscreen app/game is active, and resumes automatically once the reason clears
- **Daily-times schedule** — an alternative to a fixed interval: pick times of day ("08:00, 18:00") instead
- **Tags & collections** — tag any image and filter playback to a saved "match any of these tags" collection spanning every drive
- **Monitor topology strip** — a read-only view of your actual display arrangement (groundwork for multi-monitor wallpapers in v2.0)
- **Experimental per-monitor engine** — an opt-in `IDesktopWallpaper` COM backend lets "Set as Wallpaper" target one specific display instead of all of them; see the caveat below before relying on it with more than one monitor
- **Modern shell (v1.7+)** — four-page UI, floating HUD, tag drawer, toasts, System/Light/Dark appearance

---

## Prerequisites

- Windows 10 or Windows 11
- Python **3.10+**
- [`customtkinter`](https://github.com/TomSchimansky/CustomTkinter), [`Pillow`](https://python-pillow.org/), and [`pystray`](https://github.com/moses-palmer/pystray) (tray icon; the app still runs without it, but closing the window quits instead of minimising to tray)
- Optional: [`comtypes`](https://pypi.org/project/comtypes/) for the experimental per-monitor COM engine

---

## Installation

### Option A — prebuilt executable (no Python required)

Download `DesktopVista.exe` from the project's [Releases](https://github.com/hawkers63/Desktop-Vista/releases) page (or build it yourself — see [Building the executable](#building-the-executable)) and run it directly. It carries the branded icon and creates `config.json` beside itself on first launch.

### Option B — from source

1. Clone or copy this repository to a local folder (for example `D:\Desktop_Vista`).
2. Open PowerShell in that folder.
3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Copy the example configuration and edit it for your machine:

```powershell
Copy-Item config.example.json config.json
# Then edit config.json with your wallpaper folder paths
```

5. Launch the application:

```powershell
python desktop_vista.py
```

> **Note:** `config.json` is gitignored and must never be committed — it may contain private drive paths.

---

## Building the executable

A standalone `DesktopVista.exe` is built with [PyInstaller](https://pyinstaller.org/):

```powershell
pip install pyinstaller
pyinstaller build_exe.spec
```

The output is written to `dist\DesktopVista.exe` — a single-file, windowed (no console) build carrying `icon/desktop_vista.ico` as both the file icon and the runtime window/tray icon. See `build_exe.spec` for the exact PyInstaller configuration.

---

## Usage & shortcuts

| Key | Action |
| :--- | :--- |
| **Left** | Previous image in the current source |
| **Right** | Next image in the current source |
| **Return** | Set the current image as desktop wallpaper |
| **R** | Jump to a random image |
| **Space** | Pause / resume slideshow (v1.7+) |
| **Esc** | Dismiss overlays / leave inspection modes (v1.7+) |
| **?** | Shortcut help |
| **F11** | Inspection mode |

Use the sidebar (and v1.7+ pages/HUD) to add folders, choose fit style, set slideshow interval, toggle shuffle, and start or stop the slideshow. Previous / Random / Next controls under the preview mirror the keyboard actions.

Closing the window (✕) hides Desktop Vista to the system tray rather than quitting, as long as the tray icon started successfully. Right-click the tray icon for Open Desktop Vista, Next / Previous, Pause / Resume slideshow, Reveal in Explorer, and Exit — Exit is the way to fully quit while the tray icon is running.

---

## Configuration reference

Settings are stored in `config.json` beside `desktop_vista.py` (or beside the `.exe` when frozen). Use [`config.example.json`](config.example.json) as a template:

| Key | Type | Description |
| :--- | :--- | :--- |
| `folders` | `string[]` | Absolute paths to wallpaper directories |
| `current_folder` | `string \| null` | Folder currently selected in the UI |
| `current_image` | `string \| null` | Last selected image path (restored on launch) |
| `style` | `string` | Wallpaper fit style: `Fill`, `Fit`, `Stretch`, `Centre`, or `Span` |
| `interval` | `string` | Slideshow interval label, e.g. `"15 minutes"`, or `"Custom…"` (see app for full list) |
| `interval_custom_seconds` | `number \| null` | Seconds used when `interval` is `"Custom…"` |
| `shuffle` | `boolean` | When `true`, slideshow picks images at random |
| `tray.enabled` | `boolean` | Start the system tray icon (default `true`) |
| `tray.close_to_tray` | `boolean` | Closing the window hides to tray instead of quitting (default `true`) |
| `tray.run_at_startup` | `boolean` | Launch Desktop Vista minimised at Windows login (Run key); reflects the actual registry state, not just this file (default `false`) |
| `playlists` | `[{id, name, folders}]` | Named playlists — each aggregates images from its listed folders (union, deduplicated) |
| `favourites` | `string[]` | Favourited image paths (non-destructive) |
| `hidden` | `string[]` | Hidden image paths — filtered out of playback everywhere (non-destructive) |
| `playback_source` | `{kind, id} \| null` | The active source: `kind` is `"folder"` or `"playlist"`, `id` is a folder path or playlist id |
| `power.pause_on_battery_saver` | `boolean` | Auto-pause the slideshow while Windows Battery Saver is on (default `true`) |
| `power.pause_on_fullscreen` | `boolean` | Auto-pause while a fullscreen app/game or presentation is active (default `true`) |
| `schedule.mode` | `string` | `"interval"` (fixed interval, default) or `"daily"` (`daily_times`) |
| `schedule.daily_times` | `string[]` | 24-hour `"HH:MM"` times used when `schedule.mode` is `"daily"` |
| `tags` | `{path: string[]}` | Freeform tags per image path (non-destructive) |
| `collections` | `[{id, name, tags_any}]` | Saved filters — a collection plays every known image tagged with any of `tags_any` |
| `solar` | `{enabled, latitude, longitude, fallback_times}` | Dawn/day/dusk/night data model — stored and validated; see ROADMAP for wiring status |
| `wallpaper_target` | `string` | `"spi"` (default, global) or `"com"` (experimental per-monitor engine) |

---

## Experimental: per-monitor wallpapers

Switching "Per-monitor engine (COM)" on routes **Set as Wallpaper** through
`windows_wallpaper_com.py` (an `IDesktopWallpaper` COM backend) instead of the
default global `SystemParametersInfoW` call, and lets you pick a specific
display from the dropdown next to it instead of "All Displays". This has been
verified — on the machine this was built on — to genuinely create the COM
object, enumerate monitors, and apply to both the all-displays target and that
machine's one real monitor without error.

**What it is not yet:** that machine has a single display attached, so
**true per-monitor independence — two different images actually showing on
two different physical screens at once — has not been visually confirmed.**
There is also still only one shared navigation/slideshow state; this toggle
changes *where* the current image is applied, not a path to independent
per-monitor slideshows. Turn it off (back to `"spi"`) if anything looks wrong
on your setup — the default path is unaffected either way.

Example (placeholders only):

```json
{
  "folders": [
    "D:\\Wallpapers\\Landscapes",
    "E:\\Media\\Desktop Backgrounds"
  ],
  "current_folder": "D:\\Wallpapers\\Landscapes",
  "current_image": "D:\\Wallpapers\\Landscapes\\example_widescreen.jpg",
  "style": "Fill",
  "interval": "15 minutes",
  "shuffle": false,
  "tray": {
    "enabled": true,
    "close_to_tray": true,
    "run_at_startup": false
  }
}
```

---

## Verification

```powershell
python -m compileall -q .
python -m pytest -q
```

See [`docs/VERIFICATION.md`](docs/VERIFICATION.md) for manual Windows checks (multi-DPI, tray, COM caveats).

---

## Project layout

```
Desktop_Vista/
├── desktop_vista.py           # Main application
├── hotkeys.py / ipc.py / schedule.py / ui_components.py
├── windows_wallpaper_com.py   # Optional IDesktopWallpaper COM backend
├── build_exe.spec             # PyInstaller spec for DesktopVista.exe
├── icon/                      # Branded window/tray icon
├── config.example.json        # Safe configuration template
├── config.json                # Local settings (not tracked)
├── requirements.txt / pytest.ini
├── tests/                     # Unit tests
├── docs/                      # Verification notes
├── agents/ / notes/           # Agent briefs and design notes
├── LICENSE / README.md / CHANGELOG.md / ROADMAP.md / MEMORY.md
```

---

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for the live plan. Headline status:

- **Shipped through v1.8.1** — tray companion, playlists, power awareness, tags/collections, UI rewrite, Hidden Items / editor hygiene, a11y prep
- **Proposed v1.9** — Help & polish (Help panel, preview cache candidates, packaging discussion)
- **v2.0 multi-monitor** — deferred by decision until dual-display hardware is available for real verification

---

## Copyright & Licence

**Copyright © 2026 Mark Hawksworth (hawkers63). All Rights Reserved.**

Desktop Vista and all materials in this repository are proprietary. Unauthorised copying, reproduction, redistribution, modification, reverse-engineering, or commercial use is strictly prohibited without prior written consent from the copyright holder.

See [`LICENSE`](LICENSE) for the full notice.

---

*Desktop Vista — All my drives. One perfect view.*
