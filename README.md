# Desktop Vista

**All my drives. One perfect view.**

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows&logoColor=white)
![Licence](https://img.shields.io/badge/Licence-Proprietary%20%2F%20All%20Rights%20Reserved-red)

A lightweight Windows wallpaper manager built with CustomTkinter. Desktop Vista keeps every wallpaper folder across your drives in one dual-pane workspace, with a memory-efficient 16:9 preview engine so you can browse 4K images without loading them at full resolution.

---

## Why Desktop Vista?

Windows Background settings are awkward when your wallpapers live on several disks. Desktop Vista exists so you can:

- Organise folders on any local or external drive from a single control panel
- Preview images instantly in a fixed 16:9 frame (decoded straight to preview size, not full 4K)
- Set a wallpaper or run a folder slideshow without opening the Control Panel again and again

The layout is dual-pane: a left **control panel** for folders, fit style, and slideshow; a right **canvas** for preview, metadata, and Previous / Random / Next navigation.

---

## Key features

- **Multi-drive folder management** — add or remove wallpaper directories from any drive
- **Instantaneous 16:9 preview decoding** — Pillow decodes to preview size for a fast, light UI
- **Custom slideshow intervals** — 1 minute through 1 day
- **Shuffle engine** — optional random order during slideshows
- **Fit styles** — Fill, Fit, Stretch, Centre, Span (Windows wallpaper registry styles)
- **Keyboard navigation** — browse and apply without reaching for the mouse
- **Persistent preferences** — folders, style, interval, shuffle, and last image remembered in `config.json`

Supported image types: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`.

---

## Prerequisites

- Windows 10 or Windows 11
- Python **3.10+**
- [`customtkinter`](https://github.com/TomSchimansky/CustomTkinter) and [`Pillow`](https://python-pillow.org/)

---

## Installation

1. Clone or copy this repository to a local folder (for example `D:\Desktop_Vista`).
2. Open PowerShell in that folder.
3. Install dependencies:

```powershell
pip install customtkinter pillow
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

---

## Configuration reference

Settings are stored in `config.json` beside `desktop_vista.py`. Use [`config.example.json`](config.example.json) as a template:

| Key | Type | Description |
| :--- | :--- | :--- |
| `folders` | `string[]` | Absolute paths to wallpaper directories |
| `current_folder` | `string \| null` | Folder currently selected in the UI |
| `current_image` | `string \| null` | Last selected image path (restored on launch) |
| `style` | `string` | Wallpaper fit style: `Fill`, `Fit`, `Stretch`, `Centre`, or `Span` |
| `interval` | `string` | Slideshow interval label, e.g. `"15 minutes"` (see app for full list) |
| `shuffle` | `boolean` | When `true`, slideshow picks images at random |

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
  "shuffle": false
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

- Minimise to system tray (`pystray`) for silent slideshows
- Multi-monitor wallpaper routing

---

## Copyright & Licence

**Copyright © 2026 hawkers63. All Rights Reserved.**

Desktop Vista and all materials in this repository are proprietary. Unauthorised copying, reproduction, redistribution, modification, reverse-engineering, or commercial use is strictly prohibited without prior written consent from the copyright holder.

See [`LICENSE`](LICENSE) for the full notice.

---

*Desktop Vista — All my drives. One perfect view.*
