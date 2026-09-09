# Desktop Vista — Roadmap

**Baseline:** v1.1 (hardened) — merged via PR #1, 2026-09-09. That release covered the robustness/security audit in [`notes/notes_003.txt`](notes/notes_003.txt) (debounced saves, threaded preview decode, WebP transcode cache, Fisher–Yates shuffle, atomic config I/O, EXIF orientation, responsive preview canvas, slideshow timer lifecycle) — engineering hardening, not new user-facing features.

This document schedules the **next four releases**, drawing on the feature backlog in [`notes/notes_002.txt`](notes/notes_002.txt) and [`AGENT_1_FEATURE_INNOVATION.md`](AGENT_1_FEATURE_INNOVATION.md). Note a renumbering: notes_002 originally targeted its "Silent Companion" tray/startup bucket at v1.1, but that version number was consumed by the hardening pass instead. That bucket rolls forward into **v1.2** below, so the plan here reads v1.2 → v1.5, with v2.0 remaining the multi-monitor/COM milestone beyond this window.

---

## v1.2 — "Silent Companion"

Goal: live in the tray, survive a drive unplug, stop demanding the window stay open.

| Priority | Item | Status |
| :---: | :--- | :--- |
| P0 | `pystray` tray icon + context menu; close/minimise → `withdraw`; Exit quits cleanly | ✅ Done |
| P0 | `--minimized` launch flag + optional `HKCU\...\Run` startup entry | ✅ Done |
| P0 | Reveal in File Explorer (`explorer /select,"path"`) | ✅ Done (shipped as part of the tray menu) |
| P1 | Custom slideshow interval in seconds (`interval_custom_seconds`, schema bump) | ✅ Done |
| P1 | Offline-aware folders — skip missing files without crashing, `(offline)` badge, resume on reconnect | ✅ Done |
| P2 | Branded `.ico` (monitor + cog concept, supplied 2026-09-09) | ✅ Done — `icon/desktop_vista.ico`/`.png`, loaded via `load_brand_icon()` for the tray and `iconbitmap()` for the window; falls back to the procedural placeholder if missing |

**Exit criteria:** slideshow survives window hide; unplugging a USB drive mid-slideshow doesn't crash; app can start minimised from Windows startup.

---

## v1.2.1 — Hardening addendum

An architecture/UX review (`notes/notes_004.txt`, 2026-09-09) audited the v1.2 codebase and supplied the icon assets above. The following findings were fixed directly; the review's larger structural proposals (bounded preview LRU cache, full tray/Tk command-queue bridge, single-instance guard, `IDesktopWallpaper` COM backend, SQLite catalogue) are carried forward into v1.3+ rather than folded into this patch.

| Priority | Item | Status |
| :---: | :--- | :--- |
| High | Stale-`exc`-in-lambda `NameError` risk in the preview error callback | ✅ Fixed |
| High | Tray "Next/Previous Wallpaper" only updated the preview, never applied | ✅ Fixed — tray navigation now calls `_set_wallpaper(silent=True)` |
| Medium | Tray readiness only checked "Icon object exists", not "background thread actually started" — a failed tray could strand `--minimized` with a hidden, unrecoverable window | ✅ Fixed — explicit `threading.Event` readiness/failure signal, `--minimized` falls back to a visible window on failure |
| Medium | Switching to an empty/offline folder didn't invalidate in-flight preview loads from the previous folder | ✅ Fixed — load token bumps on every folder switch |
| Medium | `_load_preview_image` called `exif_transpose` before `draft`, undermining the fast reduced decode for rotated images | ✅ Fixed — orientation read first, draft box swapped accordingly |
| Medium | Shared mutable `DEFAULT_CONFIG["folders"]` could leak into `cfg` on a rejected field and be mutated in place | ✅ Fixed — `copy.deepcopy(DEFAULT_CONFIG)` |
| Medium | Tray boolean flags accepted via `bool(value)`, so `"false"`/`0`/`1` were silently coerced | ✅ Fixed — requires a literal `bool` |
| Medium | Non-finite (`inf`/`nan`) custom interval seconds could crash `int()` at apply time | ✅ Fixed — rejected during validation and at resolve time |
| Medium | `save_config` used a fixed `.tmp` filename — two instances writing at once could race | ✅ Fixed — unique temp file per write via `tempfile.mkstemp` |
| Medium | "Start with Windows" reported "on" from mere key existence, even after Python/script relocation | ✅ Fixed — compares the actual registry command to what this install would write today |
| Low | `_advance_shuffle` used `list.pop(0)` (O(n) shift) | ✅ Fixed — cursor-indexed deck |

Deferred to v1.3+ (see notes_004 §1, §4–5, §7): background-thread folder enumeration/offline probing off the Tk thread, a bounded byte-budgeted preview LRU cache, a formal tray/Tk command-queue bridge, single-instance ownership, and the config schema v2 migration (sources/playlists/catalogue) that those features depend on.

---

## v1.3 — "All My Drives" playlists ✅ Done (2026-09-09)

Goal: deliver the tagline — one slideshow spanning every drive, not just the folder currently selected.

| Priority | Item | Status |
| :---: | :--- | :--- |
| P0 | Playlist manager + `playback_source` config (folders ∪ playlists) | ✅ Done |
| P0 | Slideshow builds its image list from playlist membership across multiple drives | ✅ Done |
| P1 | Favourites (heart) and blacklist/hide filters — non-destructive, source files untouched | ✅ Done |
| P1 | Drive reconnect watcher (poll), building on v1.2's offline badges | ✅ Done — 15s poll, `WM_DEVICECHANGE` deferred (notes_004 Track A: "not a replacement for UNC polling", so polling alone already meets this release's bar) |

**Implementation note:** playlists/favourites/hidden/`playback_source` are additive
`config.json` fields (see `config.example.json`), not notes_004 §7's full schema v2
(stable source IDs, volume identity, SQLite catalogue). That heavier model earns its
cost once tags/collections (v1.5) or library scale need it — v1.3's own exit criteria
don't.

**Exit criteria:** one playlist spanning two drives plays correctly (✅ — the
playback source list is a folder-image union, deduplicated); favourites/hidden
filter the active slideshow without modifying source files (✅).

---

## v1.4 — Power & Context Awareness ✅ Done (2026-09-09)

Goal: behave well on laptops and stop interrupting foreground work.

| Priority | Item | Status |
| :---: | :--- | :--- |
| P0 | Battery Saver pause (`GetSystemPowerStatus`) | ✅ Done — throttle (a *different*, slower interval while on battery but Battery Saver isn't on) not implemented; only the on/off pause was in this release's exit criteria |
| P0 | Fullscreen/game suppression (`SHQueryUserNotificationState`) | ✅ Done — suppresses on `QUNS_RUNNING_D3D_FULL_SCREEN`/`QUNS_PRESENTATION_MODE` |
| P1 | Clock-time interval triggers ("every day at 08:00") alongside fixed intervals | ✅ Done — `schedule.mode: "daily"` + `schedule.daily_times` |
| P2 | Acrylic/Mica backdrop experiment on Win11 | ❌ Dropped — disproportionate implementation risk/value for this app; not revisited |

**Implementation note:** pause reasons (`battery_saver`, `fullscreen`) are tracked
independently, and slideshow "running" (user intent) is tracked separately from
whether a tick is currently scheduled — so an auto-pause can't be mistaken for
the user having stopped it, and clearing one pause reason can't accidentally
resume a slideshow that's also paused for the other. The daily-schedule trigger
is recomputed fresh from wall-clock time on every call rather than cached, so a
DST change or clock adjustment self-corrects on the next tick instead of
drifting — full DST fold/gap policy (notes_004 Track D) wasn't built out further
than that.

**Exit criteria:** slideshow auto-pauses on Battery Saver and while a fullscreen
app/game is active (✅ — verified via a mocked power/notification-state smoke
test, not a real battery-saver/fullscreen session); daily-times trigger computes
the correct next occurrence (✅ — unit tested for same-day, roll-to-tomorrow, and
exact-time-boundary cases).

---

## v1.5 — Foundations for v2.0 ✅ Done (2026-09-09)

Goal: lay organisational and topology groundwork before the multi-monitor COM rewrite, without touching the wallpaper-apply path yet.

| Priority | Item | Status |
| :---: | :--- | :--- |
| P0 | Read-only monitor topology surfaced in the UI — no per-monitor apply yet | ✅ Done — via `EnumDisplayMonitors`/`GetMonitorInfoW`, not `IDesktopWallpaper`'s `GetMonitorDevicePathAt`/`GetMonitorRECT` (COM isn't needed just to enumerate read-only; that pairing is deferred to v2.0 alongside the COM apply path itself, so device-path identity — stable across docking changes — arrives together with the code that actually needs it) |
| P1 | Smart tags + virtual collections (non-destructive metadata, cross-path, no file duplication) | ✅ Done |
| P1 | Solar/time-of-day cycle groundwork (Dawn/Day/Dusk/Night scheduling model, no live output changes required yet) | ✅ Done — data model + validation only, no UI and no scheduler wiring (out of scope for "groundwork") |
| P2 | Lock Screen WinRT setter — research spike only | ❌ Not started |

**Implementation note:** tags/collections are a third playback-source kind
(`kind: "collection"`) alongside folders and playlists — a collection's
candidate images are every tagged image inside any known folder or playlist
folder, matched on tags-any, then hidden-filtered the same way every other
source is. The monitor topology math (union-rect scaling, negative-coordinate
handling) is a pure, unit-tested function so it's reused as-is once v2.0 needs
the same layout for per-monitor assignment cards.

**Exit criteria:** the monitor strip in the UI accurately reflects the real
arrangement (✅ on this machine's single display; multi-monitor layout math
unit-tested for two-monitor and negative-coordinate cases, not visually
confirmed on real multi-monitor hardware); a tag can be applied across images
from two different drives and filtered into a virtual collection (✅).

---

## v1.6 — "Scriptable companion" ✅ Done (2026-09-09)

Goal: land everything that does not require a second physical display to be correct, per the architecture/viability review in [`notes/notes_005.txt`](notes/notes_005.txt). This is deliberately the **last single-pipeline release** — one shared image index/navigation/slideshow state, same as every release before it; independent per-monitor state is v2.0's job.

| Priority | Item | Status |
| :---: | :--- | :--- |
| P0 | Fix v1.5 defect: saved `playback_source.kind == "collection"` was dropped on restart | ✅ Done — `_validate_config`'s kind whitelist and `_resolve_initial_source` both gained a `"collection"` branch |
| P1 | Playback history ring (100 applied wallpapers) + Undo | ✅ Done — `playback_state.json`; tray "Previous" and a new "Undo Last Applied" tray item both walk applied history rather than the raw index (shuffle order isn't linear, so a deck-rewind wouldn't retrace what was actually shown) |
| P1 | 1 Hz scheduler replacing one `after(seconds * 1000)` | ✅ Done — a repeating heartbeat polls a due-time (monotonic for interval mode, wall-clock for daily/solar) instead of arming a single long timer, so a sleep/hibernate gap finds "due" true at most once on resume, never a catch-up burst |
| P1 | Solar mode wired into the live scheduler | ✅ Done — new `schedule.py` (pure, unit-tested NOAA-style sun-position math); `schedule.mode: "solar"` advances at real dawn/sunrise/sunset/dusk boundaries, biases the next pick toward phase-tagged images when the library has any, and discloses an honest unfiltered status when it doesn't |
| P1 | Single-instance mutex (`CreateMutexW`) | ✅ Done — new `ipc.py`; a second launch never opens a duplicate window, it forwards to the running instance instead |
| P1 | Named-pipe CLI IPC (`--next`, `--status`, `--set`, ...) | ✅ Done — `ipc.py`'s `IpcServer`, owner-only pipe security descriptor (SDDL, not world-accessible); the tray daemon is now scriptable from Task Scheduler/Stream Deck/a shell |
| P1 | Global hotkeys (`RegisterHotKey`) | ✅ Done — new `hotkeys.py`; a dedicated thread owns registration + the `GetMessage` loop rather than subclassing Tk's own window (avoids the WndProc-subclass GC/reentrancy hazards); default Win+Alt+N/P/L/H/Z/S, per-action rebindable in config, a bind conflict is logged and shown, never silently retried |
| P2 | Preview LRU + off-thread folder enum (notes_004 leftover, carried since v1.2.1) | ✅ Done, scoped down — no unbounded cache existed to bound, so the actual fix is (a) cancelling a still-queued stale preview decode on rapid navigation instead of letting it run to completion, and (b) moving the 15s reconnect poll's `is_folder_online`/`list_images` calls off the Tk thread, since an unreachable NAS/UNC path can block for the OS network timeout |

**Implementation note:** every new Win32 surface (mutex, named pipe, hotkeys) is ctypes-only, no pywin32, matching the rest of the app. All three were live-verified against this machine's real desktop and real running instance — not just unit tests — including a genuine `--next`/`--undo` wallpaper change and restore over the pipe, a real global hotkey firing end-to-end (`keybd_event` → `RegisterHotKey` → the app), and a measured `_on_close()` shutdown that stays under a few milliseconds for the new stop paths. One of the six default hotkey bindings (`Win+Alt+F`) collided with an existing binding on this dev machine (a driver overlay, unidentified) — swapped the shipped default to `Win+Alt+L`, discovered only by testing live rather than assuming the notes' suggested mnemonic was conflict-free.

**Exit criteria:** collection playback source survives a restart (✅, unit tested); 96 pre-v1.6 tests plus new coverage for all eight items stay green (✅ — 148/148 as of this release); `--selftest` on a frozen build reports mutex/pipe/hotkey/solar fixtures (✅, extended this release).

---

## v1.6.1 — UI hardening addendum ✅ Done (2026-09-09)

A UI/UX audit (`notes/notes_006.txt`, reviewed against commit `ce8b849`) found two real P1 defects, plus a much larger seven-track redesign proposal (see "Beyond this window — UI evolution" below). The two defects were fixed directly; the redesign proposal is scoped as a separate forward track, not folded into this patch, same pattern as v1.2.1.

| Priority | Item | Status |
| :---: | :--- | :--- |
| P1 | Keyboard shortcuts leaked into text-entry widgets — typing "forest" into the Tags field also triggered Favourite (`f`) and Random (`r`), since CTkEntry wraps a real Tk Entry and `self.bind()` on the toplevel still sees those keystrokes | ✅ Fixed — `_shortcut`/`_focus_is_text_entry` guard walks the focused widget's class/ancestry and no-ops (returns without consuming the key) while focus is inside an Entry/Text/Spinbox/Combobox |
| P1 | Fit Style dropdown was an apply command, not a staged preference — `_on_style_changed` called `set_windows_wallpaper` directly and unconditionally, always through the legacy global SPI path even with the experimental per-monitor COM engine and a specific target monitor selected | ✅ Fixed — the handler now only saves the preference; `style_var` is already read at apply time by every real apply path (`_apply_path`/`_set_wallpaper`), so the new style takes effect on the next explicit apply through whichever backend (SPI/COM) and target is actually selected |

**Verification note:** the review's live-Windows test run (mutex/pipe/hotkey, 5 of 148 failing) was re-run in this session on the same commit with nothing else on the machine holding those resources: 148/148 passed cleanly. The failure signature (mutex "not primary", pipe `ERROR_ACCESS_DENIED`, no synthetic hotkey delivery) is consistent with the review having run in a different/isolated execution context — not a code regression. Both new fixes were live-verified against this machine's real registry/focus state, not just reasoned about.

**Exit criteria (both met):** typing in the Tags field no longer triggers image actions, and shortcuts still fire normally once focus is elsewhere (verified live); changing Fit Style leaves the registry untouched until an explicit apply, and the staged value is then used correctly (verified live against `HKCU\Control Panel\Desktop\WallpaperStyle`).

---

## v1.7 — UI/interaction rewrite ✅ Done (2026-09-09)

notes_006's phases B–D, implemented in the same session as v1.6.1, per Mark's explicit go-ahead to continue through them rather than stop at the two defect fixes.

| Phase | Scope | Status |
| :---: | :--- | :--- |
| B | Four-page sidebar (Library/Playback/Displays/Settings) replacing the 11-section stack; 3-row main layout (context header / stage / permanent footer); three button rows consolidated into one floating HUD | ✅ Done — pages are built once and shown via `grid()`/`grid_remove()` (never rebuilt, state survives a switch); footer's single "Apply to `<target>`" button reads live from the COM target selection |
| C | Tag inspector/chips; Hidden Items shows parent folder + offline badge (was basename-only) with a search filter; toast notifications alongside the persistent status line | ✅ Done, editor drafts **not** done — playlist/collection editors keep their existing fixed-geometry dialogs (see below) |
| D | Dark/light/system appearance switch; shortcut help overlay; inspection mode (F11, fit-to-screen only) | ✅ Done, Narrator/high-contrast/multi-DPI verification **not** performed — needs real assistive-technology and multi-monitor hardware, same honesty gate notes_006 itself set |

**New files:** `ui_components.py` — the four blueprint components from notes_006 §4 (`ActionButton`, `HoverHUD`, `ToastManager`, `TagSelector`), adopted close to verbatim (one bug fixed: an 8-digit `#RRGGBBAA` colour isn't valid Tk — Tk has no colour-alpha syntax — swapped for a solid token colour).

**Keyboard remap (documented behaviour change, notes_006 §2.7):** Space now starts/stops the slideshow (was Next); Esc now closes the active panel — tag drawer, shortcut help, inspection mode — instead of stopping the slideshow. A one-time in-app notice fires on first launch after update (`cfg.ui.seen_shortcut_notice_v2`); the Playback page's Start/Stop button remains the always-visible non-keyboard way to stop the slideshow, as notes_006 required before making this change.

**New `cfg["ui"]` namespace** (presentation-only preferences, validated like every other section): `selected_page`, `appearance`, `hud_always_visible`, `reduced_motion`, `seen_shortcut_notice_v2`.

**Deliberately not done this release:**
- Playlist/collection editor redesign (draft-copy-on-open, inline validation, two-line friendly/path display) — the dialogs are unchanged from v1.6; only Hidden Items got the specific fix (parent-folder disambiguation) because that was an actual functional gap (identical filenames on different drives were indistinguishable), not a polish item.
- Interactive per-display output map (phase E) — still correctly blocked on notes_005 §2.1.4's Win32/COM display-identity reconciliation; the topology strip stays read-only.
- Accent sync, ambient glow, drag-to-assign (phase F) — v2.1-scope polish, unstarted.
- `_apply_path`'s COM call can still block the Tk thread up to 5s with no async dispatch — that's notes_005's v2.0 `ApplyQueue`, not a v1.7-sized fix.

**Verification:** live-tested against this machine's real config/registry, not just constructed-in-isolation — page switching, HUD button dispatch (Favourite toggle round-tripped through `cfg["favourites"]`), the tag drawer (add/remove round-tripped through `cfg["tags"]`, confirmed the keyboard guard still holds inside its own Entry), the Escape chain, the Space→slideshow remap, inspection-mode Toplevel open/close, and `ui` preference persistence through a real save/reload — all via property-based checks (`grid_info()`/`winfo_viewable()`, not `winfo_ismapped()`, which is unreliable for `CTkScrollableFrame`'s own composite window — verified against a standalone repro). The full real subprocess (`python desktop_vista.py --minimized`) was also exercised end-to-end over the same IPC pipe as v1.6: `--next`/`--undo` correctly round-tripped a real wallpaper change through the rewritten stage and preview pipeline. No screenshots were used for verification after an early one accidentally captured the full physical screen (not just the app window) and briefly exposed unrelated on-screen content; deleted immediately, and no further screen/window capture was attempted for the rest of this pass.

**Exit criteria:** all old actions remain reachable at the 980×560 minimum (✅, nothing was removed, only relocated); current settings round-trip unchanged (✅, 152/152 tests passing including new config-schema coverage for `cfg["ui"]`); exact canonical tag semantics preserved (✅, case-sensitive exact-string, live-verified); duplicate filenames/offline paths distinguishable in Hidden Items (✅, live-verified); editing tags never navigates/applies and Fit preview stays side-effect free (✅, carried from v1.6.1).

---

## Next five releases (scoped from notes_007 / notes_008, 2026-09-09)

An architecture pack (`notes/notes_007.txt`, Principal Systems Architect role) and Mark's own
condensed priority note (`notes/notes_008.txt`) agree on scope for the next five releases. Read
together they replace this document's old open-ended "Beyond this window" musings with concrete,
gated plans:

| Release | Theme | Readiness |
| :--- | :--- | :--- |
| **v1.8** | Leftover closure (single pipeline) | ✅ Done (2026-09-10) |
| **v1.8.1** | Accessibility verification gate | ⏳ Blocked — needs Mark + real Narrator on Windows 11 |
| **v2.0** | "One Perfect View" display rewrite | ⏳ Blocked — needs 2+ physical displays + a dock/undock cycle |
| **v2.1** | Intelligence & scale | ⏳ Blocked — depends on v2.0's assignment model existing |
| **Future / research gate** | dhash/ONNX saliency, extra cloud feeds, per-monitor fullscreen, desktop crossfade | ⏳ Blocked — sequenced after v2.1, some items may never ship (see notes_007 §2 "Deliberate non-features") |

Only v1.8 is unblocked by anything other than engineering time, so it's the release under
active development this session.

## v1.8 — Leftover closure (single pipeline) ✅ Done (2026-09-10)

Closes the five items Mark named plus two prep items, all correctness/UI work that does **not**
require a second physical display. Explicitly excludes ApplyQueue, SQLite, a clickable topology
map, and anything else that belongs to v2.0+ (notes_007 §6.5).

| Priority | Item | Status |
| :---: | :--- | :--- |
| P0/P1 | Hidden Items playback-invariant rebuild (`_rebuild_playback_after_filter_change`) — hide/unhide no longer desyncs `self.images`/index/shuffle deck | ✅ Done |
| P1 | Hide-of-applied advances the desktop through the existing silent apply path (or honestly leaves the last image if the source is now empty) | ✅ Done |
| P2 | Hidden manager hygiene: `_folder_online_cache` instead of a Tk-thread probe, Reveal in Explorer per row, explicit off-thread "Remove missing" | ✅ Done |
| P1/P2 | Playlist/collection `EditorSheet` + `TagSelector` reuse + playlist "Browse…" + live match-count + inline validation | ✅ Done |
| Low | About/copyright block on Settings + tray "About Desktop Vista…" entry | ✅ Done |
| Med | Read-only topology: session RECT join (`join_monitor_topology`) for display labels, unresolved (ambiguous) displays flagged — still no click handler | ✅ Done |
| Med | Keyboard tab-order audit + `SPI_GETHIGHCONTRAST` honour + `--selftest` DPI dump + Narrator test script written into `VERIFICATION.md` | ✅ Done — tab order audited via a standalone Tk traversal probe (no code change needed, see `VERIFICATION.md`); high-contrast honour and per-monitor DPI dump implemented; Narrator/contrast/multi-DPI hardware pass itself is v1.8.1 |

**Exit criteria (all met):** 171/171 tests passing (was 152); `APP_VERSION` → `"1.8"`.

**Implementation note:** also fixed a latent pre-existing bug found while wiring high-contrast
honour — the app always launched in dark mode regardless of the saved `cfg["ui"]["appearance"]`
preference, because `ctk.set_appearance_mode("dark")` was hardcoded before config load and never
re-applied at startup (only on an explicit dropdown change). Folded into `_apply_appearance_mode`,
called once after config load and again on every appearance change.

## v1.8.1 — Accessibility verification gate

No feature work if v1.8's tab-order/contrast/DPI groundwork lands cleanly. Mark (or a designated
tester) runs the `VERIFICATION.md` Narrator script on real Windows 11 — Light/Dark, 100%/150%
scaling. Outcomes recorded as pass / fail / toolkit-limitation; a fake pass is never recorded.

## v2.0 — "One Perfect View" (display rewrite)

See "Beyond this window — v2.0" below for the full item list and exit criteria. Non-negotiable
prerequisites: a machine with 2+ physical displays attached, at least one dock/undock or Win+P
cycle during verification, and `ApplyQueue` landed before any UI claims "Applying…". Extracts
`playback.py` (PlaybackController) and `displays.py` (topology join, fingerprinting, span slicer).

## v2.1 — Intelligence and scale

SQLite catalogue (`desktop_vista.db`) with dual-write of tags/favourites/hidden back to
`config.json`, weather-reactive bias (Open-Meteo, opt-in, no API key), opt-in Windows accent-colour
sync (Pillow quantize, never NumPy), lock-screen WinRT research spike against the frozen exe,
perceptual-duplicate review UI, resolution down-rank, EXIF inspector, entropy focal-point crop,
Bing Daily/NASA APOD feeds. Only starts once v2.0's per-display assignment model exists — a
catalogue's `display_assignments` table would otherwise encode a fiction.

## Future / research gate

Lightweight ONNX saliency (exe-size risk), Unsplash/Wallhaven feeds (ToS/API-key risk),
per-monitor fullscreen detection (`HWND ∩ RECT`), desktop crossfade (research gate, no committed
direction). Mica/Acrylic on Tk stays **dropped** (notes_005/v1.4 call, reaffirmed in notes_007).

---

## Beyond this window — UI evolution (notes_006, phases E–F)

Phases A–D above are done. What's left from notes_006's seven-track proposal:

| Phase | Proposed release | Scope | Blocked on |
| :---: | :--- | :--- | :--- |
| E | v2.0 dependency | Interactive per-display output map, per-display applied thumbnails, span crop assistant | A reconciled Win32/COM display identity model and real per-target state — notes_005 §2.1.4's fingerprinting scheme, part of the v2.0 milestone itself |
| F | v2.1 optional | Accent sync; ambient glow; drag-to-assign staging; advanced polish | Nothing structural — just sequenced after v2.0/v2.1 per notes_005's own plan |

Also still open: `_apply_path`'s COM call can block the Tk thread for up to 5 seconds with no way to stay responsive during it (needs async dispatch — notes_005's v2.0 `ApplyQueue`); the playlist/collection editors' draft-state/inline-validation redesign (notes_006 §2.5) was scoped as part of phase C but not implemented — the dialogs work, they just don't have the proposed Save/Cancel-draft-copy or inline field errors yet; full Narrator/high-contrast/multi-DPI accessibility verification.

---

## Beyond this window — v2.0 "One Perfect View"

`IDesktopWallpaper` COM integration for true per-monitor wallpapers, panoramic/ultrawide span assist, independent per-monitor playback state, and a go/no-go decision on desktop crossfade. Solar cycles are wired into the applied wallpaper already (v1.6, against the single shared pipeline); v2.0's job is giving each display its own index/navigation/slideshow/solar state instead of one shared one. The legacy `SystemParametersInfoW` path stays live behind a `wallpaper_target` feature flag until the COM path is proven (see `notes/notes_002.txt` §5 cross-cutting notes).

### v1.5.1 — v2.0 groundwork landed (2026-09-09)

Shipped ahead of the full milestone, gated behind `wallpaper_target: "com"` (default stays `"spi"`, zero behaviour change unless opted in):

| Item | Status |
| :--- | :--- |
| `windows_wallpaper_com.py` — real `IDesktopWallpaper` COM backend (comtypes), one dedicated STA thread, blocking call dispatch | ✅ Done |
| UI: per-monitor engine toggle + target-monitor picker; "Set as Wallpaper" routes through COM when enabled | ✅ Done |
| Verify COM plumbing: object creation, monitor enumeration, `SetWallpaper`/`SetPosition` for the all-displays target and this machine's one real monitor-specific target | ✅ Done — both visibly changed the desktop, cross-checked against `SystemParametersInfoW`'s own reported path |
| Verify true per-monitor independence (two different images, two different physical displays, neither affecting the other) | ❌ **Not verified** — this development machine has one display attached; do not treat this as confirmed until checked on real multi-monitor hardware |

**Still ahead for the full v2.0 milestone** (none of this is done):

- Independent per-monitor playback state — v1.6 kept one shared image index/navigation/slideshow/schedule (interval, daily, and now solar) across the whole app; a real per-monitor experience needs separate assignment and (per the wireframes) possibly separate slideshows per display, per notes_005 §2.1's `PlaybackController`/`ApplyQueue` design.
- Span crop assistant and mixed-DPI/portrait-display validation (notes_004 Track B, notes_005 §2.1.3).
- Device-path persistence/reconciliation across docking or driver changes (`GetMonitorDevicePathAt` identity is not guaranteed stable — notes_004 Track B, notes_005 §2.1.4's fingerprinting scheme).
- Desktop crossfade go/no-go (research gate — no committed direction).
- Lock Screen WinRT setter (carried over from v1.5, still just a research spike — notes_005 §2.3.2 has the spike plan).
- SQLite catalogue, weather bias, accent-colour sync, curation (focal crop/dedupe/EXIF), curated feeds — all scoped to **v2.1** in notes_005, deliberately after v2.0 since a catalogue's `display_assignments` table would encode a fiction before per-monitor assignment exists.

---

## Notes

- Version numbers above are release numbers, not calendar dates — fit the cadence to actual capacity.
- Update `notes/notes_002.txt`'s schema/wireframe sections as each release's config keys land, and keep `config.example.json` in sync. `config.json` itself stays gitignored.
- Source backlog: `notes/notes_001.txt` (design intent), `notes/notes_002.txt` (feature matrix + phased plan), `notes/notes_003.txt` (v1.1 hardening audit), `notes/notes_004.txt` (v1.2 architecture/UX review + supplied icon assets), `notes/notes_005.txt` (v1.6 → v2.1 functional/systems architecture pack — viability matrix, module blueprints, DB schema, phased plan), `notes/notes_006.txt` (UI/UX audit + phases A–F redesign proposal, reviewed against v1.6/`ce8b849`), `AGENT_1_FEATURE_INNOVATION.md`, `AGENT_5_FUNCTIONAL_ENHANCEMENTS.md` (the brief notes_005 was written against), `AGENT_4_UI_IMPROVEMENTS.md` (the brief notes_006 was written against).
