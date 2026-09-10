# Changelog

All notable releases of Desktop Vista. Detailed GitHub Release notes remain authoritative for each tag.

## Unreleased

- Closed multi-DPI scaling clip check (100% / 125% / 150% / 200% Pass) after live Windows testing
- ROADMAP: v2.0 marked deferred by decision (no dual-monitor hardware on actual-use machines); proposed v1.9 Help & polish; distribution/packaging discussion recorded as background
- Repo tidy: `tests/`, `docs/`, `agents/` layout; master agent docs on `main`

## 1.8.1 — 2026-09-10

Leftover closure and walkthrough fixes on top of v1.8.

- Renamed `_apply_appearance_mode` to avoid a CustomTkinter method-name collision that crashed launch
- Sidebar nav row layout gap fixed
- Tab order / contrast pass; multi-DPI selftest groundwork (clip check closed post-tag on `main`)

GitHub Release: [v1.8.1](https://github.com/hawkers63/Desktop-Vista/releases/tag/v1.8.1)

## 1.8 — 2026-09-10

- Hidden Items playback invariants (single rebuild path; safe mid-slideshow hide)
- Hidden manager hygiene (online cache, Reveal, remove-missing)
- Reusable `EditorSheet`; About / copyright in Settings and tray
- Read-only topology join labels; a11y prep (high-contrast, `--selftest` DPI)

## 1.7 — 2026-09-09

UI rewrite: four-page shell, floating HUD, tag drawer, toasts, appearance modes, Space/Esc/?/F11 shortcuts, Hidden Items improvements, `cfg["ui"]` namespace.

GitHub Release: [v1.7](https://github.com/hawkers63/Desktop-Vista/releases/tag/v1.7)

## 1.6 / 1.6.1

Scriptable companion — history/undo, solar scheduling, single-instance IPC, global hotkeys; keyboard / Fit-Style defect fixes.

## 1.2 — 2026-09-09

Silent Companion: system tray, Start-with-Windows, Reveal in Explorer, custom interval seconds, offline-aware folders.

GitHub Release: [v1.2](https://github.com/hawkers63/Desktop-Vista/releases/tag/v1.2)

## 1.1 and earlier

Hardened dual-pane wallpaper browser baseline (debounced saves, threaded preview decode, WebP cache, Fisher-Yates shuffle, atomic config I/O, EXIF orientation, slideshow timer lifecycle).
