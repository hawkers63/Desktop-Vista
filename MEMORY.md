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
