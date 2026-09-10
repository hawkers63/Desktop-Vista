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

**Result, 2026-09-10 (Mark, this dev machine, Windows 11):** Apply, the Source menu, Hide,
Favourite, Tags, Hidden Items' Unhide/Reveal/Remove missing, and Start/Stop Slideshow were all
silent — including Start/Stop Slideshow with genuine Win32 keyboard focus on it (not just
Narrator's scan cursor), ruling out "scan mode hasn't refreshed" as the explanation. "Fit Style"
and "All Displays" (both `CTkOptionMenu`) did announce. A small, seemingly arbitrary set of
Library-page items also announced (app title, tagline, Hidden Items, New Playlist, New
Collection) despite being built identically (plain `ctk.CTkButton`) to items that didn't.

**Root-caused, not just observed:** queried this app's live window directly with both the modern
UI Automation API (`IUIAutomation`) and the legacy MSAA API (`IAccessible`/`AccessibleChildren`)
via a throwaway read-only script (COM calls only — no clicks, no state changes). Findings:
- UIA: the entire Tk client area is exactly two unnamed, childless elements. No widget, page, or
  piece of text is exposed this way at all.
- MSAA: every child window returns only the generic default Windows window-chrome Windows
  synthesizes automatically for any window (title-bar buttons, scrollbars) — recursively
  duplicated, and otherwise empty. Filtering that boilerplate out of an 864-line, depth-8 dump of
  the *entire* window left a single unnamed "graphic" element and nothing else.

Conclusion: neither accessibility API exposes any real application content. **Tk/CustomTkinter
provides no accessible tree for this app to hook into, full stop** — not "an incomplete one," an
empty one. Whatever Narrator announced was not coming from either API; it is almost certainly
Narrator's own fallback of reading a focused window's raw caption text for specific HWNDs, which
depends on incidental internals of how each widget happens to be constructed rather than any
documented contract. This cannot be made consistent from application code — there is no
accessibility surface underneath to attach a fix to, and the project has already (correctly)
ruled out building a fake UIA provider to simulate one. Recorded as **toolkit limitation** for
Narrator scan mode as a whole, not a per-control defect list.

### Contrast

- [x] Turn on Windows high contrast (Settings → Accessibility → Contrast themes). The app should
      switch to CTk's "system" tokens automatically (`_apply_ui_appearance_mode` /
      `is_high_contrast_active`, SPI_GETHIGHCONTRAST) rather than fighting it with a saved
      light/dark preference. Confirm your saved preference re-applies once high contrast is
      turned back off. **Pass, 2026-09-10 (Mark):** everything stays visible under contrast
      themes; saved preference returns correctly once turned off.
- [x] In Light and in Dark (high contrast off), check text-on-fill contrast is comfortably
      readable against Win11's default accent colours. **Pass, 2026-09-10:** no issues detected.

### Multi-DPI

- [x] Run `python desktop_vista.py --selftest` (or the frozen `.exe --selftest`) and record its
      "Per-monitor DPI (GetDpiForMonitor)" and "Tk scaling factor" lines here for this machine —
      this is the measurement the v2.0 mixed-DPI span-crop work starts from, not an assumption.
      **2026-09-10, this machine (single 1920x1080 display, 100% Windows scaling):**
      `Per-monitor DPI (GetDpiForMonitor): [{'device': '\\\\.\\DISPLAY1', 'dpi_x': 96, 'dpi_y': 96}]`,
      `Tk scaling factor: 1.3333333333333333`.
- [ ] At 125% / 150% / 200% Windows scaling, confirm nothing required for the app's exit criteria
      is clipped at the 980×560 minimum window size. **Not yet run** — this dev machine's display
      is currently at 100% scaling; needs an actual Windows scaling change to test.

### Outcomes (fill in per pass)

| Date | Tester | Windows build | Narrator scan mode | Contrast | Multi-DPI | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-09-10 | Mark | Windows 11 Home 10.0.26100 | Toolkit limitation (root-caused via direct UIA/MSAA query — see above) | Pass | Partial (100% scaling measured; 125/150/200% not yet tried) | Tab order/focus (§ above): pass |

## Linux / CI note

Unit tests import `desktop_vista` without opening a window. Wallpaper apply and the full GUI are Windows-only; helpers (`list_images`, config, transcode, shuffle) are exercised on Linux.
