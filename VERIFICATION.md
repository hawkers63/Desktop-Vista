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

## v1.8 — Accessibility verification (manual, real hardware/AT required)

Per notes_007 §1.4 / §6.2: CustomTkinter is a drawing toolkit on top of Tk and does not
automatically expose a complete UIA tree. This app does not, and will not, claim "Narrator
support" — a toast-based fake announcement layer would certify a fiction. What follows is a
script for a real pass with real Windows Narrator, run by Mark or a designated tester, with
honest pass / fail / toolkit-limitation outcomes recorded below rather than a green ROADMAP tick.

**Prerequisites:** Windows 11, Narrator (Win+Ctrl+Enter), a build at or after v1.8.

### Tab order and focus (can be checked without Narrator running)

1. Launch the app. Press Tab repeatedly from the nav rail. Expected order: nav rail buttons →
   the active sidebar page's controls top-to-bottom → stage header → HUD (reveal it first with
   the "Controls" button or by hovering the stage — a hidden HUD is `place_forget()`'d and must
   never receive focus) → footer Apply → status.
2. Switch sidebar pages (Library/Playback/Displays/Settings) and confirm Tab never lands on a
   control belonging to a page that isn't currently shown. **Audited in code, 2026-09-10:**
   pages use `grid()`/`grid_remove()` and the tag drawer / shortcut-help overlay use
   `place()`/`place_forget()`; a standalone Tk probe confirmed `tk_focusNext` (the traversal Tab
   invokes by default) already skips both `grid_remove()`'d and `place_forget()`'d widgets via
   their `winfo_ismapped()` state — so a page or overlay that is hidden this way cannot become a
   focus stop. This is an architecture-level guarantee, not something that needs auditing per
   widget, and did not require any code change.
3. Open the Playlist or Collection editor (`EditorSheet`). Tab should stay inside the modal
   (Save/Cancel reachable); Esc must cancel with no cfg write, matching a click on Cancel.

### Narrator scan mode

Turn on Narrator (Win+Ctrl+Enter) and, using only Narrator's scan mode (no mouse), reach and
activate each of:

- [ ] Apply (footer)
- [ ] Start/Stop slideshow (Playback page)
- [ ] Source menu (Library page)
- [ ] Hide (HUD)
- [ ] Favourite (HUD)
- [ ] Tags (opens the tag drawer; TagSelector entry/chips are reachable)
- [ ] Hidden Items → Unhide / Reveal / Remove missing
- [ ] Playlist/Collection editor Save / Cancel

For each: does Narrator announce a sensible name and role? Record pass / fail / "toolkit
limitation" (Tk/CTk exposes nothing meaningful here) — a toolkit limitation is not a bug to fix
with a fake provider, it's a documented boundary.

### Contrast

- [ ] Turn on Windows high contrast (Settings → Accessibility → Contrast themes). The app should
      switch to CTk's "system" tokens automatically (`_apply_appearance_mode` /
      `is_high_contrast_active`, SPI_GETHIGHCONTRAST) rather than fighting it with a saved
      light/dark preference. Confirm your saved preference re-applies once high contrast is
      turned back off.
- [ ] In Light and in Dark (high contrast off), check text-on-fill contrast is comfortably
      readable against Win11's default accent colours.

### Multi-DPI

- [ ] Run `python desktop_vista.py --selftest` (or the frozen `.exe --selftest`) and record its
      "Per-monitor DPI (GetDpiForMonitor)" and "Tk scaling factor" lines here for this machine —
      this is the measurement the v2.0 mixed-DPI span-crop work starts from, not an assumption.
- [ ] At 125% / 150% / 200% Windows scaling, confirm nothing required for the app's exit criteria
      is clipped at the 980×560 minimum window size.

### Outcomes (fill in per pass)

| Date | Tester | Windows build | Narrator scan mode | Contrast | Multi-DPI | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| | | | | | | |

## Linux / CI note

Unit tests import `desktop_vista` without opening a window. Wallpaper apply and the full GUI are Windows-only; helpers (`list_images`, config, transcode, shuffle) are exercised on Linux.
