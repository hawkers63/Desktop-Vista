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

## Beyond this window — v2.0 "One Perfect View"

`IDesktopWallpaper` COM integration for true per-monitor wallpapers, panoramic/ultrawide span assist, wiring tags/collections and solar cycles into the *applied* wallpaper (not just the UI), and a go/no-go decision on desktop crossfade. The legacy `SystemParametersInfoW` path stays live behind a `wallpaper_target` feature flag until the COM path is proven (see `notes/notes_002.txt` §5 cross-cutting notes).

---

## Notes

- Version numbers above are release numbers, not calendar dates — fit the cadence to actual capacity.
- Update `notes/notes_002.txt`'s schema/wireframe sections as each release's config keys land, and keep `config.example.json` in sync. `config.json` itself stays gitignored.
- Source backlog: `notes/notes_001.txt` (design intent), `notes/notes_002.txt` (feature matrix + phased plan), `notes/notes_003.txt` (v1.1 hardening audit), `notes/notes_004.txt` (v1.2 architecture/UX review + supplied icon assets), `AGENT_1_FEATURE_INNOVATION.md`.
