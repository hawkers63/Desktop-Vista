# Desktop Vista — Verification (v1.1 hardened)

## Automated tests

From the project directory:

```bash
cd /workspace/Desktop_Vista   # or D:\Desktop_Vista on Windows
pip install -r requirements.txt
pytest -q
```

Expected: all tests pass (no display required). Coverage includes:

- `load_config` defaults, corrupt JSON recovery, missing/invalid keys
- Atomic `save_config` round-trip and `.tmp` cleanup
- `list_images` sorting and empty result for missing/unreadable paths
- WebP → JPEG cache under a temporary cache directory
- Fisher–Yates shuffle deck: full index coverage; skip-current behaviour

Run a single file or node:

```bash
pytest test_desktop_vista.py -q
pytest test_desktop_vista.py::test_ensure_wallpaper_webp_creates_cache -q
```

## Manual UI checks (Windows)

1. **Launch** — `python desktop_vista.py` (Windows). Confirm dark UI and tagline.
2. **Add folder** — Add a folder with JPG/PNG/WebP mix. Status shows image count.
3. **Preview** — Navigate with buttons, Left/Right, Space, Backspace, `p`, `r`/`R`. Preview updates without UI freeze on large files.
4. **Resize** — Stretch the window; preview stays roughly 16:9 and re-renders.
5. **Debounced save** — Flip through images quickly; `config.json` should not rewrite on every keypress (check mtime). Quit the app; last image is persisted.
6. **Restore** — Relaunch; last folder and image appear once (no double flash at index 0).
7. **WebP wallpaper** — Select a `.webp`, press Set as Wallpaper. Desktop updates; a `.jpg` appears under `%LOCALAPPDATA%\DesktopVista\cache\`.
8. **Fit style** — Change Fill → Fit (etc.) with an image selected; wallpaper style updates without pressing Set again.
9. **Slideshow** — Start slideshow; wait one interval. Manually press Next; confirm the next auto-advance waits a full interval again. Escape stops slideshow. Empty/unreadable folder stops or refuses start.
10. **Shuffle** — Enable Shuffle; advance via Random / slideshow; confirm images cycle without immediate repeats of the same file when more than one image exists.
11. **Unreadable drive** — Point at a disconnected path (or remove permissions); UI shows empty/unreadable status rather than crashing.
12. **Close** — Quit via window chrome; no hung threads; config written; no leftover `config.json.tmp`.

## Linux / CI note

Unit tests import `desktop_vista` without opening a window. Wallpaper apply and the full GUI are Windows-only; helpers (`list_images`, config, transcode, shuffle) are exercised on Linux.
