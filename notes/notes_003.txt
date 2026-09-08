# Desktop Vista — Security & Robustness Audit (v1.0 → v1.1 hardened)

Severity scale: **Critical** · **High** · **Medium** · **Low** · **Info**

---

## 1. Synchronous save on every preview navigation — **High**

**Root cause:** `_show_current` called `_save()`, which wrote `config.json` on every Previous/Next/Random and every slideshow tick. Rapid navigation caused excessive disk I/O and raised the chance of a torn write if the process exited mid-write.

**Fix:** Debounced save (`SAVE_DEBOUNCE_MS` ≈ 600 ms) via `after()`. `_show_current` only schedules a save. Immediate flush (`_flush_save` / `_write_config`) on shutdown, folder switch, style/interval changes, and folder removal.

---

## 2. UI-thread image decode — **High**

**Root cause:** Full image open + thumbnail ran on the Tk main thread inside `_show_current`, freezing the UI on large (e.g. 4K/8K) files.

**Fix:** `ThreadPoolExecutor` loads and thumbnails off-thread. A monotonic `_load_token` drops stale results. UI updates are marshalled with `self.after(0, ...)`.

---

## 3. WebP (and other non-native formats) fail as wallpaper — **High**

**Root cause:** `SystemParametersInfoW` accepts `.jpg` / `.jpeg` / `.bmp` / `.png` reliably. Passing `.webp` often silently fails or does nothing.

**Fix:** `ensure_wallpaper_path()` returns the source path for native extensions; otherwise transcodes (with EXIF transpose) to a JPEG under `%LOCALAPPDATA%\DesktopVista\cache` (or temp), keyed by SHA-256 of path + mtime + size.

---

## 4. Slideshow timer not reset on manual navigation; jobs leak on close — **Medium**

**Root cause:** Manual Previous/Next/Random left the existing `after` deadline in place, so the next tick could fire almost immediately. `_on_close` did not cancel slideshow (or other) `after` jobs before `destroy()`.

**Fix:** `_reset_slideshow_timer_if_running()` on manual nav. Slideshow stops when the image list is empty. `_cancel_after_jobs()` runs in `_on_close` before destroy; executor is shut down.

---

## 5. Restore state double-shows / wrong index — **Medium**

**Root cause:** `_restore_state` called `_load_folder`, which always set `index = 0` and called `_show_current`, then overwrote the index with the last image and showed again — flicker and an extra save.

**Fix:** `_load_folder(..., show=False)` for restore; set index to last image if present; call `_show_current` once.

---

## 6. Missing EXIF orientation — **Medium**

**Root cause:** Phone/camera JPEGs often store orientation in EXIF. Preview and wallpaper used the raw pixel matrix, appearing rotated.

**Fix:** `ImageOps.exif_transpose` after open in preview load and wallpaper transcode paths.

---

## 7. Fit style change did not reapply wallpaper — **Medium**

**Root cause:** Style option menu only called `_save()`, so the desktop kept the previous Windows `WallpaperStyle` until the user pressed “Set as Wallpaper”.

**Fix:** `_on_style_changed` flushes config and calls `set_windows_wallpaper` with the current image when one is selected (no-op / logged on non-Windows).

---

## 8. Random navigation was with-replacement — **Low**

**Root cause:** `_random` used `random.choice` excluding only the current index, so images could repeat before all had been seen; no shuffle deck.

**Fix:** Fisher–Yates `build_shuffle_deck()` maintains `_shuffle_order`; deplete then reshuffle; skip current as first draw when possible.

---

## 9. Non-atomic config write; weak validation — **Medium**

**Root cause:** `save_config` used `Path.write_text` in place. `load_config` merged JSON without type checks — a corrupt or hand-edited file could put non-lists/invalid styles into runtime state.

**Fix:** Write `config.json.tmp` then `os.replace`. `load_config` / `_validate_config` check folders (list of str), style ∈ `WALLPAPER_STYLES`, interval ∈ `SLIDESHOW_INTERVALS`, shuffle bool, etc., and fall back to defaults.

---

## 10. `list_images` missed broad I/O failures — **Medium**

**Root cause:** Only `FileNotFoundError` and `PermissionError` were caught. Offline network drives and other `OSError` subclasses (and some `ValueError` path cases) could crash folder load.

**Fix:** Catch `OSError` and `ValueError`; return `[]` and surface “empty or unreadable” status in the UI.

---

## 11. Fixed preview size; incomplete keyboard map — **Low**

**Root cause:** Preview always targeted 800×450 regardless of window size. Shortcuts covered Left/Right/Enter/r only.

**Fix:** Track `_preview_size`; bind `<Configure>` on preview/main to recompute a 16:9 box (with hysteresis). Bindings: Space = next, Backspace / `p` = previous, Escape = stop slideshow, `r` / `R` = random.

---

## Additional hardening (Info)

| Item | Notes |
|------|--------|
| Structured logging | `logging` module replaces ad-hoc `print` for config/I/O warnings. |
| Platform imports | `winreg` / `ctypes` guarded so the module imports on Linux for unit tests. |
| British English | User-facing strings retain “Centre”, “Unauthorised”, etc. |
| Version | Docstring bumped to **1.1 hardened**. |
