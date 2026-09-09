# Desktop Vista

**All my drives. One perfect view.**

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows&logoColor=white)
![Licence](https://img.shields.io/badge/Licence-Proprietary%20%2F%20All%20Rights%20Reserved-red)

A lightweight Windows wallpaper manager built with CustomTkinter. Desktop Vista gathers wallpaper folders from every local and external drive into one dual-pane workspace, and pairs that with a memory-efficient 16:9 preview engine so you can browse large (including 4K) images without decoding them at full resolution.

---

## Why Desktop Vista?

Windows Background settings become awkward when wallpapers live across several disks. Desktop Vista exists so you can:

- Keep every wallpaper folder — internal, USB, or network-mapped — in one control panel
- Preview candidates instantly in a fixed 16:9 frame (decoded straight to preview size)
- Apply a single image or run a folder slideshow without returning to the Control Panel

The dual-pane layout is intentional: a left **control panel** for folders, fit style, and slideshow; a right **canvas** for preview, metadata, and Previous / Random / Next navigation. Browse on the right; manage sources and timing on the left.

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

---

## Prerequisites

- Windows 10 or Windows 11
- Python **3.10+**
- [`customtkinter`](https://github.com/TomSchimansky/CustomTkinter), [`Pillow`](https://python-pillow.org/), and [`pystray`](https://github.com/moses-palmer/pystray) (tray icon; the app still runs without it, but closing the window quits instead of minimising to tray)

---

## Installation

1. Clone or copy this repository to a local folder (for example `D:\Desktop_Vista`).
2. Open PowerShell in that folder.
3. Install dependencies:

```powershell
pip install customtkinter pillow pystray
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

## Usage & shortcuts

| Key | Action |
| :--- | :--- |
| **Left** | Previous image in the current folder |
| **Right** | Next image in the current folder |
| **Return** | Set the current image as desktop wallpaper |
| **R** | Jump to a random image in the current folder |

Use the sidebar to add folders, choose fit style, set slideshow interval, toggle shuffle, and start or stop the slideshow. Previous / Random / Next buttons under the preview mirror the keyboard actions.

Closing the window (✕) hides Desktop Vista to the system tray rather than quitting, as long as the tray icon started successfully. Right-click the tray icon for Open Desktop Vista, Next / Previous, Pause / Resume slideshow, Reveal in Explorer, and Exit — Exit is the way to fully quit while the tray icon is running.

---

## Configuration reference

Settings are stored in `config.json` beside `desktop_vista.py`. Use [`config.example.json`](config.example.json) as a template:

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

## Project layout

```
Desktop_Vista/
├── desktop_vista.py      # Main application
├── config.example.json   # Safe configuration template
├── config.json           # Local settings (not tracked)
├── LICENSE               # Proprietary — All Rights Reserved
├── README.md             # This file
└── notes/                # Design and scope notes
```

---

## Roadmap (planned)

See [`ROADMAP.md`](ROADMAP.md) for the full four-release plan (v1.2 → v1.5) — tray/background automation, cross-drive playlists, power awareness, and monitor-topology groundwork ahead of the v2.0 multi-monitor rewrite.

---

## Copyright & Licence

**Copyright © 2026 Mark Hawksworth. All Rights Reserved.**

Desktop Vista and all materials in this repository are proprietary. Unauthorised copying, reproduction, redistribution, modification, reverse-engineering, or commercial use is strictly prohibited without prior written consent from the copyright holder.

See [`LICENSE`](LICENSE) for the full notice.

---

*Desktop Vista — All my drives. One perfect view.*
