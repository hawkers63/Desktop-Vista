# Desktop Vista — Roadmap

**Baseline:** v1.1 (hardened) — merged via PR #1, 2026-09-09. That release covered the robustness/security audit in [`notes/notes_003.txt`](notes/notes_003.txt) (debounced saves, threaded preview decode, WebP transcode cache, Fisher–Yates shuffle, atomic config I/O, EXIF orientation, responsive preview canvas, slideshow timer lifecycle) — engineering hardening, not new user-facing features.

This document schedules the **next four releases**, drawing on the feature backlog in [`notes/notes_002.txt`](notes/notes_002.txt) and [`AGENT_1_FEATURE_INNOVATION.md`](AGENT_1_FEATURE_INNOVATION.md). Note a renumbering: notes_002 originally targeted its "Silent Companion" tray/startup bucket at v1.1, but that version number was consumed by the hardening pass instead. That bucket rolls forward into **v1.2** below, so the plan here reads v1.2 → v1.5, with v2.0 remaining the multi-monitor/COM milestone beyond this window.

---

## v1.2 — "Silent Companion"

Goal: live in the tray, survive a drive unplug, stop demanding the window stay open.

| Priority | Item |
| :---: | :--- |
| P0 | `pystray` tray icon + context menu; close/minimise → `withdraw`; Exit quits cleanly |
| P0 | `--minimized` launch flag + optional `HKCU\...\Run` startup entry |
| P0 | Reveal in File Explorer (`explorer /select,"path"`) |
| P1 | Custom slideshow interval in seconds (`interval_custom_seconds`, schema bump) |
| P1 | Offline-aware folders — skip missing files without crashing, `(offline)` badge, resume on reconnect |
| P2 | Branded `.ico` (Framed Landscape or Floating Displays concept from `notes/notes_001.txt`) |

**Exit criteria:** slideshow survives window hide; unplugging a USB drive mid-slideshow doesn't crash; app can start minimised from Windows startup.

---

## v1.3 — "All My Drives" playlists

Goal: deliver the tagline — one slideshow spanning every drive, not just the folder currently selected.

| Priority | Item |
| :---: | :--- |
| P0 | Playlist manager + `playback_source` config (folders ∪ playlists) |
| P0 | Slideshow builds its image list from playlist membership across multiple drives |
| P1 | Favourites (heart) and blacklist/hide filters — non-destructive, source files untouched |
| P1 | Drive reconnect watcher (poll or `WM_DEVICECHANGE`), building on v1.2's offline badges |

**Exit criteria:** one playlist spanning two drives plays correctly; favourites/blacklist filter the active slideshow without modifying source files.

---

## v1.4 — Power & Context Awareness

Goal: behave well on laptops and stop interrupting foreground work.

| Priority | Item |
| :---: | :--- |
| P0 | Battery Saver pause/throttle (`GetSystemPowerStatus`) |
| P0 | Fullscreen/game suppression (`SHQueryUserNotificationState`) |
| P1 | Clock-time interval triggers ("every day at 08:00") alongside fixed intervals |
| P2 | Acrylic/Mica backdrop experiment on Win11 (optional; may slip to v1.5) |

**Exit criteria:** slideshow auto-pauses on Battery Saver and while a fullscreen app/game is active; clock-time trigger fires within the same tick tolerance as fixed intervals.

---

## v1.5 — Foundations for v2.0

Goal: lay organisational and topology groundwork before the multi-monitor COM rewrite, without touching the wallpaper-apply path yet.

| Priority | Item |
| :---: | :--- |
| P0 | Read-only monitor topology (`GetMonitorDevicePathAt`, `GetMonitorRECT`) surfaced in the UI — no per-monitor apply yet |
| P1 | Smart tags + virtual collections (non-destructive metadata, cross-path, no file duplication) |
| P1 | Solar/time-of-day cycle groundwork (Dawn/Day/Dusk/Night scheduling model, no live output changes required yet) |
| P2 | Lock Screen WinRT setter — research spike only |

**Exit criteria:** the monitor strip in the UI accurately reflects the real arrangement; a tag can be applied across images from two different drives and filtered into a virtual collection.

---

## Beyond this window — v2.0 "One Perfect View"

`IDesktopWallpaper` COM integration for true per-monitor wallpapers, panoramic/ultrawide span assist, wiring tags/collections and solar cycles into the *applied* wallpaper (not just the UI), and a go/no-go decision on desktop crossfade. The legacy `SystemParametersInfoW` path stays live behind a `wallpaper_target` feature flag until the COM path is proven (see `notes/notes_002.txt` §5 cross-cutting notes).

---

## Notes

- Version numbers above are release numbers, not calendar dates — fit the cadence to actual capacity.
- Update `notes/notes_002.txt`'s schema/wireframe sections as each release's config keys land, and keep `config.example.json` in sync. `config.json` itself stays gitignored.
- Source backlog: `notes/notes_001.txt` (design intent), `notes/notes_002.txt` (feature matrix + phased plan), `notes/notes_003.txt` (v1.1 hardening audit), `AGENT_1_FEATURE_INNOVATION.md`.
