# Desktop Vista — Project Memory

Keyword to resume this thread with Claude: **"Let's get started"**

This file lives in the project directory itself (`D:\Desktop_Vista\MEMORY.md`)
so continuity notes stay in one place with the code. It was previously kept
externally at `D:\Claude.Memory\MEMORY.d`; that file holds the history up to
2026-09-09 and is no longer appended to.

---

## 2026-09-09 — Roadmap for v1.2 → v1.5 established

**Context:** Desktop Vista v1.1 (hardened) shipped via PR #1 (debounced saves, threaded
preview decode, WebP transcode cache, Fisher–Yates shuffle, atomic config I/O, EXIF
orientation fixes — see `D:\Desktop_Vista\notes\notes_003.txt`). This was a
robustness/security pass, not the "Silent Companion" feature set that
`notes/notes_002.txt` had originally scheduled for v1.1.

**Decision:** Renumbered the notes_002 feature backlog into four releases:
- **v1.2** "Silent Companion" — tray icon/menu, `--minimized` startup, Reveal in
  Explorer, custom interval seconds, offline-aware folders, branded icon.
- **v1.3** "All My Drives" — cross-drive playlist manager, favourites/blacklist,
  drive reconnect watcher.
- **v1.4** Power & Context Awareness — battery saver pause, fullscreen/game
  suppression, clock-time interval triggers.
- **v1.5** Foundations for v2.0 — read-only monitor topology, tags/virtual
  collections, solar-cycle groundwork (no live wallpaper changes yet).
- **v2.0** (beyond this window) — `IDesktopWallpaper` COM per-monitor wallpapers,
  ultrawide span assist, tags/solar wired into the applied wallpaper, crossfade
  go/no-go.

Full detail in `D:\Desktop_Vista\ROADMAP.md`.

**Repo conventions to remember:**
- Repo: `D:\Desktop_Vista` (git; GitHub remote under `hawkers63`; proprietary /
  all-rights-reserved license; copyright Mark Hawksworth).
- `notes/` holds numbered running notes: `notes_001.txt` (design intent),
  `notes_002.txt` (feature/UX backlog + phased plan), `notes_003.txt` (v1.1
  hardening audit — formerly `AUDIT.md` at repo root), `notes_004.txt` (v1.2
  architecture/UX review + supplied icon assets). Keep using `notes_[N].txt`
  for new note packs.
- Three "agent brief" docs at repo root (`AGENT_1_FEATURE_INNOVATION.md`,
  `AGENT_2_CODEBASE_HARDENING.md`, `AGENT_3_GITHUB_MANAGEMENT.md`) define the
  review/build process this project runs work through — check these before
  assuming scope on a new task.
- `config.json` is gitignored (real drive paths live in it); `config.example.json`
  is the tracked template — keep both in sync whenever the schema changes.

**Still open / follow-up for next session:**
- Branded `.ico` asset (Framed Landscape / Floating Displays concept from
  `notes_001.txt`) still needs to be generated or sourced — no icon file exists
  in the repo yet; tray currently uses a procedural placeholder
  (`build_tray_icon_image()` in `desktop_vista.py`).
- That's the last open v1.2 item. Next up on "Let's get started" is either
  sourcing that icon, or moving on to v1.3 ("All My Drives" playlists).

## 2026-09-09 (later) — v1.2 implemented (all but the branded icon)

Built and pushed to `origin/main` in this session, in order:
- **Tray icon + menu** (commit 612fe63): `pystray` tray icon, dynamic menu
  (current image, Next/Previous, Pause/Resume slideshow, Reveal in Explorer,
  Open Desktop Vista, Exit). Close-to-tray by default, falls back to normal
  quit if pystray/tray APIs are unavailable. `config.tray {enabled,
  close_to_tray}`.
- **`--minimized` + Start with Windows** (commit 5c5a5f6): CLI flag launches
  hidden to tray; a sidebar switch manages a `HKCU\...\Run` entry (uses
  `pythonw.exe` to avoid a console flash). Switch state is read from the real
  registry every launch, not trusted from config. `config.tray.run_at_startup`.
- **Custom interval + offline-aware folders** (commit 33da61c): a
  "Custom…" slideshow interval prompts for seconds
  (`config.interval_custom_seconds`); the folder dropdown badges
  unreachable folders `(offline)`; most importantly, the *unattended*
  slideshow path (`_set_wallpaper(silent=True)`) now logs+skips on a
  missing file instead of popping a blocking `messagebox.showerror` that
  would otherwise freeze the slideshow until someone dismisses it — manual
  "Set as Wallpaper" still shows the dialog since a person is at the
  keyboard.
- ROADMAP.md updated to mark all of this done (commit a6b9110).

41/41 unit tests passing throughout (`pytest test_desktop_vista.py`).
Registry-touching tests mock `dv.winreg` rather than hitting the real
`HKCU\...\Run` key.

## 2026-09-09 (later still) — v1.2.1 hardening pass + first .exe build

**Context:** Mark dropped `notes/notes_004.txt` — a full architecture/UX
review of the v1.2 codebase (bug catalog, feature matrix, COM/playlist
blueprints for v1.3+) plus supplied icon assets (`icon/001.ico` + numbered
PNGs — a blue rounded-tile monitor+cog glyph). Asked to use it to amend
scope, continue development, and finish with a built `.exe`.

**Fixed (pushed as commits f2b24fd, 2b6a14b, 07fe8f4, 76a0a59, 9c46500):**
- Branded window/tray icon (rebuilt as a proper 16–256px multi-resolution
  `.ico` from the largest supplied PNG — the original had only one 128px
  frame).
- Tray Next/Previous now actually apply the wallpaper, not just the preview.
- Explicit tray-readiness event so `--minimized` can't hide the window
  behind a tray that failed to start.
- Stale-exception closure bug in the preview error callback; preview-load
  token not invalidated on switching to an empty/offline folder; a shared
  mutable `DEFAULT_CONFIG` default that a rejected field could alias and
  later mutate; non-bool tray flags and non-finite custom intervals
  silently accepted; a fixed temp filename in `save_config` (two-instance
  race); EXIF orientation read after (not before) Pillow's fast `draft()`;
  `list.pop(0)` in the shuffle deck; `is_startup_enabled()` only checking
  key existence, not whether the command still matches this install.

**Deliberately deferred to v1.3+:** everything structural from notes_004 —
moving folder enumeration off the Tk thread, a bounded preview LRU cache,
a formal tray/Tk command-queue bridge, single-instance guard, and the
config schema v2 / SQLite catalogue / COM per-monitor backend that
playlists and multi-monitor depend on. ROADMAP.md now has a v1.2.1 table
listing all of this explicitly.

**`.exe` build:** `build_exe.spec` (PyInstaller, single-file, windowed).
Two gotchas worth remembering — `Path(__file__)` resolves inside the temp
`sys._MEIPASS` extraction dir in a frozen build, not beside the real
`.exe`, so `desktop_vista.py` now branches on `sys.frozen` for
`APP_DIR`/`RESOURCE_DIR`; and Pillow's PyInstaller hook pulls in numpy
(+ OpenBLAS DLL) just because it's installed in the build env, with zero
NumPy usage in the app — `excludes=["numpy"]` cut the exe from ~30MB to
~19MB. Sent `DesktopVista.exe` directly to Mark rather than a GitHub
release (his choice when asked).

50/50 tests passing (41 prior + 9 new).

## 2026-09-09 (later still) — v1.3 → v1.5 scoped, implementation underway

Mark asked to outline scope for v1.3-v2.0 and continue implementing through
them in the same session. Scope settled on:
- **v1.3**: playlists/favourites/hidden/reconnect-watcher via **additive
  JSON config fields** (`playlists`, `favourites`, `hidden`,
  `playback_source`), not notes_004's full SQLite catalogue + schema v2 —
  the simpler model covers v1.3's actual exit criteria without a risky
  migration.
- **v1.4**: Battery Saver pause, fullscreen suppression, independent
  pause-reasons, clock-time schedule mode. Dropped the optional Mica/Acrylic
  item as disproportionate risk/value for a Tk app.
- **v1.5**: read-only monitor topology via Win32 `EnumDisplayMonitors` (no
  COM needed for read-only), tags + virtual collections, solar data model
  only (not wired into playback — that's v2.0's job).
- **v2.0**: checked this machine first — one display attached, no
  `comtypes` installed. Building the `IDesktopWallpaper` backend behind an
  opt-in experimental flag (default stays the current global SPI path);
  can verify the COM plumbing but not true per-monitor visual independence
  without a second screen — flagged that honestly rather than claiming it's
  confirmed.

See ROADMAP.md for the authoritative per-release status as this lands.

## 2026-09-09 (later still) — v1.3, v1.4, v1.5, v1.5.1 all shipped in one session

Continued straight through the four-release plan per Mark's request. All
pushed to `origin/main`; ROADMAP.md has the full per-release exit-criteria
detail. Summary:

- **v1.3** (commit 5dc188b): playlists/favourites/hidden/reconnect-watcher,
  additive config fields (not the full schema-v2/SQLite catalogue notes_004
  proposed — simpler model, same exit criteria). Also fixed a real latent
  bug found while smoke-testing teardown: `<Configure>` events during
  window close could resubmit decode work to an already-shut-down
  executor (`_show_current()` now checks `self._closing`).
- **v1.4** (commit c749bfe): Battery Saver + fullscreen auto-pause as
  independently tracked pause reasons; slideshow "running" (user intent)
  now tracked separately from "a tick is scheduled" so auto-pause can
  resume itself via a 5s poll without racing manual Start/Stop; daily-times
  schedule mode recomputes fresh each tick (self-corrects across DST/clock
  changes rather than caching a stale target).
- **v1.5** (commit 6a9b7b3): read-only monitor topology (Win32
  `EnumDisplayMonitors`, no COM needed for read-only), tags + collections
  as a third playback-source kind, solar dawn/day/dusk/night data model
  (validated, stored, deliberately NOT wired into playback yet).
- **v1.5.1** (commit cc60436): `windows_wallpaper_com.py` — a real
  `IDesktopWallpaper` COM backend behind an opt-in `wallpaper_target: "com"`
  flag (default stays `"spi"`). Verified on this machine (one display):
  COM object creation, monitor enumeration, and apply-to-all/apply-to-one-
  real-monitor all work and visibly change the desktop, confirmed
  identically inside the frozen PyInstaller build via the new
  `--selftest` CLI flag. **Not verified anywhere: true per-monitor
  independence** (two different images, two different physical
  displays) — no second monitor was available to check. That's why this
  shipped as 1.5.1, not 2.0: the full v2.0 milestone (independent
  per-monitor playback state, span assist, solar/tags wired into what's
  actually applied, crossfade decision) is still ahead.

96/96 tests passing throughout. Rebuilt and re-sent `DesktopVista.exe`
(PyInstaller, ~19.5MB) reflecting all of this.

**Side note for future sessions:** ad hoc smoke tests in this session
called `_set_wallpaper()`/COM `set_wallpaper()` for real, which changes
this machine's actual desktop wallpaper (not sandboxed). Restored it to
Mark's real configured wallpaper (`C:\Program Files\Glow\Windows 11 -
Glow1.jpg`, Fill style) after each round of testing — worth doing again
if a future session's smoke tests touch the wallpaper-apply path.

**Next up:** v1.3-v1.5.1 exhausts the four-release plan from the first
"Let's get started" session. Remaining open threads: the full v2.0
milestone (see ROADMAP.md's "Still ahead" list under v1.5.1), or circling
back to notes_004's deferred structural items (preview LRU cache, tray/Tk
command-queue bridge, single-instance guard) that were explicitly
carried forward rather than done in the v1.2.1 pass.

## 2026-09-09 (later still) — v1.6 "Scriptable companion" shipped

**Context:** Mark dropped `notes/notes_005.txt` — a Grok-authored
functional/systems architecture pack (matching `AGENT_5_FUNCTIONAL_
ENHANCEMENTS.md`'s brief, saved under the filename `PROMPTS_OVERVIEW.md`
had reassigned to a *different*, not-yet-produced UI redesign pack —
flagged the mismatch, proceeded on the functional content since that's
what was actually there). Asked to continue the scope/roadmap; picked up
notes_005's own recommended next session — all 8 of its v1.6 items, in
its stated order — matching this project's established rhythm.

**Shipped, all in one session, all unit-tested and live-verified against
this real machine (not just mocked):**
- Fixed a real v1.5 defect: `playback_source.kind == "collection"` was
  silently dropped on restart (`_validate_config`'s whitelist and
  `_resolve_initial_source` both lacked a collection branch).
- Playback history ring (100 applied, `playback_state.json`) + Undo; tray
  "Previous" now walks applied history rather than decrementing the raw
  index (shuffle isn't linear, so a deck-rewind wouldn't retrace what was
  actually shown).
- Replaced the single `after(seconds * 1000)` slideshow timer with a 1 Hz
  heartbeat polling a due-time (monotonic for interval, wall-clock for
  daily/solar) — a sleep/hibernate gap now finds "due" true at most once
  on resume instead of bursting missed ticks.
- Solar dawn/day/dusk/night wired into live playback via new, pure
  `schedule.py` (NOAA-style sun-position math, unit tested against a
  London fixture and a Svalbard polar fixture).
- New `ipc.py`: `CreateMutexW` single-instance guard + a named-pipe CLI/
  scripting bridge (`--next/--status/--set/...`), owner-only pipe ACL via
  SDDL (not world-accessible).
- New `hotkeys.py`: global hotkeys via `RegisterHotKey` on a **dedicated
  thread** running its own `GetMessage` loop — deliberately *not*
  notes_005's suggested WndProc-subclass-of-Tk's-own-window approach,
  which carries real GC-lifetime/reentrancy hazards; the thread-owned
  message queue is the standard, safer pattern for a hotkey confined to no
  particular window. Default Win+Alt+N/P/L/H/Z/S.
- Preview-decode cancellation on rapid navigation (a burst of 500
  navigations now triggers ~3 real decodes, not 500) + moved the 15s
  reconnect poll's folder-online/listing probes off the Tk thread (an
  unreachable NAS/UNC path could previously freeze the whole window for
  the OS network timeout, every 15 seconds, forever).

**Live-verification highlights (this machine, real desktop, real running
instance — same hazard MEMORY.md already flags: these tests really do
change the actual wallpaper):**
- `--status`/`--next`/`--undo` over the real pipe genuinely changed and
  restored the real desktop wallpaper (`C:\Program Files\Glow\Windows 11
  - Glow1.jpg` → `Glow12.jpg` → back).
- A second `python desktop_vista.py` launch with no argv correctly
  deferred to the running instance (single process the whole time, "ok":
  true reply) instead of opening a duplicate window.
- A *real* physical hotkey fired via `keybd_event` (Win+Alt+S) flipped the
  running instance's slideshow state end-to-end.
- One of the six default bindings (`Win+Alt+F`, notes_005's suggested
  mnemonic for "favourite") turned out to already be claimed by something
  else on this machine (`ERROR_HOTKEY_ALREADY_REGISTERED`, confirmed via a
  standalone `RegisterHotKey` probe after killing the test instance) —
  swapped the shipped default to `Win+Alt+L`. Only found by testing live;
  the conflict-detection code path itself worked correctly (logged it,
  didn't retry/steal, kept the other five bindings).
- Measured `_on_close()` shutdown timing after adding the new stop paths:
  each of `_stop_ipc_server()`/`_stop_hotkeys()` completes in <1ms: no
  deadlock from the IPC server's self-connect wake-up trick (worth
  re-checking if that pattern is copied elsewhere — the ordering that
  makes it safe is `_stop_event.set()` strictly *before* the wake-up
  `send_command` call, so the server thread skips dispatch entirely
  instead of trying to marshal onto a Tk thread that's mid-shutdown).

148/148 tests passing (up from 96 at the start of this session), across
`test_desktop_vista.py`, `test_schedule.py`, `test_ipc.py`, `test_hotkeys.py`.
`--selftest` extended to cover mutex/pipe/hotkey/solar fixtures.
APP_VERSION bumped to "1.6".

**Still open:** the UI redesign pack (`AGENT_4_UI_IMPROVEMENTS.md`'s
brief) has not been produced under any filename — see the note left in
ROADMAP.md. The full v2.0 milestone (independent per-monitor playback,
span assist, device-path reconciliation) is next per notes_005's own
sequencing; v2.1 (SQLite catalogue, weather, accent sync, curation, feeds)
waits on v2.0's assignment model existing first.

## 2026-09-09 (later still) — v1.6.1 UI hardening from notes_006's audit

**Context:** Mark dropped `notes/notes_006.txt` — the UI redesign pack
that had been flagged as missing (above), authored by a different agent
("CODEX") reviewing the actual v1.6/`ce8b849` source rather than the
stale v1.5.1 brief. A rigorous, source-anchored document: executive UX
scorecard, seven redesign tracks, ASCII wireframes, four tested
CustomTkinter component blueprints (focusable button, hover HUD, toast
manager, tag chip selector), and an explicit phase A–F rollout — plus its
own honestly-reported verification run.

**First checked the verification discrepancy before acting on anything
else:** notes_006 reported 5/148 test failures (mutex "not primary", pipe
`ERROR_ACCESS_DENIED`, no synthetic hotkey delivery) on the *same* commit
this session had left at 148/148. Re-ran the full suite live, on this
machine, with nothing else holding those OS resources: clean 148/148.
The failure signature is what a different/isolated execution context
looks like for these three live-Windows surfaces (different security
principal → pipe ACL denies it; a non-interactive session → no real
`keybd_event` delivery; something else already primary → mutex fails) —
not a code regression. notes_006's own evidence section was already
appropriately cautious about this ("root cause was not proved... do not
quote 148/148 as today's outcome"); confirmed it doesn't need repair.

**Fixed both of notes_006's real P1 defects** (the well-specified ones;
see ROADMAP.md's v1.6.1 table for the two-column task/exit-criteria
version) — deliberately did **not** touch the much larger phase B–F
redesign (four-page sidebar, floating HUD replacing the three button
rows, toast system, tag chips, keyboard remap) in this pass:
- Keyboard shortcuts leaking into text entry: reproduced live first
  (typing "forest" into the Tags field really did fire Favourite on 'f'
  and Random on 'r' — CTkEntry's internal native Entry is what
  `focus_get()` returns, and it's still in the toplevel's bindtags).
  Fixed with a focus-class guard (`_focus_is_text_entry`) wrapping every
  single-key binding (`_shortcut`); verified both that the leak is gone
  and that the shortcuts still fire normally once focus is elsewhere.
- Fit Style as an unstaged apply command: `_on_style_changed` used to
  call `set_windows_wallpaper` directly and unconditionally — always the
  legacy SPI path, even with the experimental COM engine and a specific
  monitor selected, so a "preparatory" dropdown could silently restamp
  every display. Now just saves the preference; every real apply path
  already reads `style_var` at apply time. Verified live against the real
  `HKCU\Control Panel\Desktop\WallpaperStyle` value: unchanged on dropdown
  change, correctly updated on the next explicit apply. Restored the
  registry to Mark's real "Fill" afterward.

**Scoped, not implemented:** ROADMAP.md now carries notes_006's full
phase A–F table under "Beyond this window — UI evolution" (mirroring how
notes_005 was incorporated), plus the findings not yet actioned (dual
Win32/COM display identity with no shared mapping; the COM apply's
blocking-up-to-5s call with no async dispatch; the proposed Space/Esc
keyboard remap — a deliberate behaviour change, explicitly not bundled
into the phase-A guard fix). Did not start phase B (the four-page
sidebar / HUD rewrite) without checking scope first — unlike v1.6's
backend work, this changes daily interaction patterns (remapped
shortcuts, replaced button rows) and is large enough (comparable to all
of v1.6) to warrant confirming how far to go before committing to it in
one sitting.

**Testing hazard note (worth repeating for future sessions):** constructing
`DesktopVista()` directly from an ad hoc script — even one that only reads
`app.cfg`/`app.style_var` — still runs `load_config()`/`_on_close()`
against the *real* `config.json` and can touch the real registry/
wallpaper if `_set_wallpaper`/`_apply_path` gets called. Every live check
this session was run against the real file/registry and explicitly
verified restored afterward (`config.json`'s `folders`/`style`/`hotkeys`
back to Mark's actual values; `WallpaperStyle` back to `10`/Fill).

## 2026-09-09 (later still) — v1.7 UI/interaction rewrite (notes_006 phases B-D)

**Context:** After the two v1.6.1 defect fixes, asked whether to continue
through notes_006's much larger phases B-D (a genuine UI/interaction
rewrite — four-page sidebar, HUD replacing three button rows, toast
system, tag chips, a keyboard remap) in the same sitting. Mark chose
"continue through B-D now... commit at the end" — same pace as every
prior session's full-arc pass.

**Shipped:** new `ui_components.py` (notes_006 §4's four blueprint
components — `ActionButton`, `HoverHUD`, `ToastManager`, `TagSelector` —
adopted close to verbatim); `_build_ui` rewritten into four task pages
(Library/Playback/Displays/Settings) behind a nav rail, built once and
shown via `grid()`/`grid_remove()` so widget state survives a page
switch; the three stacked button rows replaced by a floating HUD; a
permanent stage footer (filename/status + one Apply button whose label
tracks the live COM target); tag editing moved to a chip drawer
(captures the image path on open so a delayed edit can't land on a
different image after navigation); toasts layered alongside the existing
persistent status line (kept as the compatibility bridge, not replaced);
System/Light/Dark appearance switching (the monitor-topology Canvas
restyled too, since CTk colour tuples don't reach raw Canvas); Space/Esc
keyboard remap with a one-time in-app notice; F11 inspection mode
(fit-to-screen only, no zoom/pan — matches notes_006's own phased scope);
`?` shortcut help overlay; Hidden Items now shows parent folder + offline
badge (fixed a real gap — same-named files on different drives were
previously indistinguishable) plus a search filter. New `cfg["ui"]`
namespace for presentation-only preferences, validated like every other
config section.

**Bug found and fixed mid-implementation:** `stage_tags_label` was given
an 8-digit `#RRGGBBAA` fg_color — Tk has no colour-alpha syntax, that's a
CSS convention that doesn't exist here — crashed on construction with
`invalid color name`. Also one `FOCUS` reference that needed to be
`ui_components.FOCUS` (namespacing slip). Both caught by actually
constructing the app, not just by syntax-checking.

**Scoped, not implemented:** the playlist/collection editors keep their
existing fixed-geometry dialogs — notes_006's draft-copy-on-open/inline-
validation redesign (§2.5) wasn't done; only Hidden Items got fixed,
since that was a genuine functional gap, not a polish item. Phase E
(interactive per-display output map) correctly stays blocked on
notes_005's display-identity reconciliation (v2.0 work). Phase F (accent
sync, ambient glow, drag-to-assign) is v2.1-scope, untouched. No
Narrator/high-contrast/multi-DPI verification — notes_006 itself flagged
that as needing real assistive-tech and hardware, not something to fake.

**Verification approach, and an incident worth remembering:** most of
this was verified by actually constructing `DesktopVista()` in a script
and driving it with `app.update()` — valid for anything synchronous
(page switching, HUD dispatch, tag round-trip, Escape chain, appearance
switching), but **`self.after(0, ...)` calls from a background thread
(the preview decoder, the reconnect prober) need a genuinely running
`mainloop()`** — an `app.update()` loop doesn't set Tk's internal
"in mainloop" flag, so those calls raise `RuntimeError: main thread is
not in main loop` that has nothing to do with real app correctness. Hit
this exact class of false alarm twice this session (once for the
reconnect-probe freeze test in the v1.6 pass, once here for preview-decode
readiness) — the fix both times was cross-checking against the real
subprocess (`python desktop_vista.py --minimized` + the IPC pipe from
v1.6), which showed `--next`/`--undo` genuinely round-tripping a real
wallpaper change through the rewritten stage. **Worth remembering for any
future session:** if an `app.update()`-loop test reports a background-
thread callback never landing, check whether it's this mainloop
restriction before treating it as a real bug.

**Safety incident — do not repeat:** one verification attempt used
`PIL.ImageGrab.grab()` (full-screen capture) to screenshot the running
app for visual review. It captured Mark's entire physical screen, not
just the app window, at a moment when a GitHub two-factor-authentication
setup page with a live QR code happened to be on screen, along with
various logged-in browser tabs. Deleted the file immediately and never
viewed or transmitted it further; no further screen/window capture was
attempted for the rest of this pass — property-based checks (`grid_info`,
`winfo_viewable`, widget `.cget()`) plus the real-subprocess/IPC approach
covered everything needed without it. **If a future session genuinely
needs a visual check of this app: do not use whole-screen capture.**
Restrict to the specific window's own reported rectangle
(`winfo_rootx/y/width/height`) after confirming via `winfo_viewable()`
that it's really the window on screen, or better, ask Mark to look at the
running app himself.

**Also hit again this session:** constructing `DesktopVista()` directly
in throwaway test scripts keeps writing to the *real* `config.json`
(and, in one case, real registry `WallpaperStyle`) — this time including
a hidden-manager test that left two fake paths in `cfg["hidden"]`. All
caught and restored before finishing (folders/style/hotkeys/hidden/ui
prefs back to Mark's real values, `seen_shortcut_notice_v2` deliberately
left `false` so *he* sees the one-time shortcut-remap notice himself on
next real launch, not a version already "consumed" by test runs).

APP_VERSION bumped to "1.7". 152/152 tests passing (up from 148).
`DesktopVista.exe` rebuilt and re-sent to Mark reflecting all of it.

---

## 2026-09-10 — v1.8 "Leftover closure" shipped; five-release scope set

**Context:** Mark dropped `notes/notes_007.txt` (Principal Systems Architect design pack) and
`notes/notes_008.txt` (his own condensed priority note) and asked for a structured scope across
the next five releases, then to start on whatever was actually ready. Both notes agreed: v1.8
closes the single-pipeline leftovers named in the v1.7 pass; v1.8.1 (Narrator/AT), v2.0 (display
rewrite), and v2.1 (catalogue/intelligence) are all gated on hardware or a human running a script
that doesn't exist on this one-display dev machine. Wrote the five-release structure into
`ROADMAP.md` and built v1.8 — the only release not blocked by anything but engineering time — in
full, across four commits (`d6f8f87`..`df2328c`).

**What shipped:**
- **Hidden Items playback invariants** — the real functional gap, not the v1.7 label fix.
  `_rebuild_playback_after_filter_change` (backed by a pure `resolve_rebuilt_index`) is now the
  one path every Hide/Unhide/editor-Save-of-the-active-source mutation of
  `self.images`/index/shuffle-deck goes through, closing an `IndexError`/wrong-file risk that was
  reachable from the HUD Hide button, `H`, and Win+Alt+H mid-slideshow. Hiding the applied
  wallpaper (or hiding anything while the slideshow runs) now silently advances the desktop
  through the existing apply path instead of only updating the preview.
- **Hidden manager hygiene** — reads `_folder_online_cache` instead of probing
  `is_folder_online()` on the Tk thread during rebuild (same freeze class v1.6 already fixed for
  the sidebar); added a per-row Reveal button and an explicit, off-thread "Remove missing" action.
- **`ui_components.EditorSheet`** — a reusable modal draft shell (persistent inline error label,
  Save disabled while invalid, Cancel/Esc/window-close all genuinely no-op on cfg). Playlist
  editor gained "Browse…"; collection editor now uses the same `TagSelector` as the main tag
  drawer instead of a raw comma box (was a real semantics-drift risk) plus a live, off-thread
  match count (`collection_match_count`).
- **About/copyright disclosure** — Settings block + "Licence notice" viewer + tray entry, one
  `ABOUT_COPY` source for both.
- **Read-only topology joined labels** — `join_monitor_topology`, a pure max-area-RECT-
  intersection join between the Win32 GDI topology and the COM device-path list. Ties (clone
  displays) or no overlap report unresolved, never guessed. Only attempted if a COM backend
  already exists (never spins one up just to label the strip) — still no click handler, that
  stays blocked on v2.0's fingerprint/reconciliation scheme.
- **a11y prep** — `is_high_contrast_active` (SPI_GETHIGHCONTRAST) wired through a new
  `_apply_appearance_mode`, which also fixed a real latent bug it exposed: appearance mode was
  hardcoded to `"dark"` at startup regardless of the saved preference, only ever corrected after
  an explicit dropdown change. `--selftest` now dumps per-monitor DPI (`GetDpiForMonitor`) and
  Tk's scaling factor. **Tab-order finding:** a standalone Tk probe (not this app, a throwaway
  script) confirmed `tk_focusNext` already excludes `grid_remove()`'d and `place_forget()`'d
  widgets via `winfo_ismapped()` — hidden pages/overlays cannot become focus stops, and no code
  change was needed for the thing notes_007 flagged. Full Narrator/contrast/multi-DPI script
  written into `VERIFICATION.md` for the v1.8.1 hardware gate — not run this session (needs real
  AT and a human).

**Not done live this session, by design:** did not construct a real `DesktopVista()` against a
config this time (unlike the v1.7 session's throwaway smoke tests, which twice needed manual
restoration of `config.json`/registry state afterward — see the incident above). All v1.8 logic
that could be pulled into pure functions (`resolve_rebuilt_index`, `collection_match_count`,
`join_monitor_topology`, `is_high_contrast_active`) has unit coverage instead; the new dialogs
(EditorSheet-based playlist/collection editors, hidden manager changes, About page) were reviewed
carefully and lint-checked (`pyflakes` clean) but **not interactively clicked through in a running
window** — flagged explicitly to Mark rather than claimed as verified. `--selftest` was run for
real on this machine and confirmed clean (no lingering process afterward).

APP_VERSION bumped to "1.8". 171/171 tests passing (up from 152). Commits not yet pushed to
`origin/main` — local `main` is 4 commits ahead, pending Mark's go-ahead.
