# Copyright (c) 2026 hawkers63. All Rights Reserved.
"""Unit tests for Desktop Vista helpers (no display / Tk required)."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image

import desktop_vista as dv


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

def test_load_config_defaults_when_missing(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(dv, "CONFIG_PATH", cfg_path)
    cfg = dv.load_config()
    assert cfg == dv.DEFAULT_CONFIG
    assert cfg is not dv.DEFAULT_CONFIG  # copy


def test_load_config_corrupt_json_recovers(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text("{ not json", encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["folders"] == []
    assert cfg["style"] == "Fill"
    assert cfg["interval"] == "15 minutes"
    assert cfg["shuffle"] is False


def test_load_config_missing_keys_filled(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"folders": ["/a"]}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["folders"] == ["/a"]
    assert cfg["style"] == "Fill"
    assert cfg["interval"] == "15 minutes"
    assert cfg["shuffle"] is False
    assert cfg["current_folder"] is None
    assert cfg["current_image"] is None
    assert cfg["interval_custom_seconds"] is None


def test_load_config_invalid_types_fall_back(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "folders": "not-a-list",
                "style": "Bogus",
                "interval": 123,
                "shuffle": "yes",
                "current_folder": 99,
                "current_image": [],
                "interval_custom_seconds": "soon",
            }
        ),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["folders"] == []
    assert cfg["style"] == "Fill"
    assert cfg["interval"] == "15 minutes"
    assert cfg["shuffle"] is False
    assert cfg["current_folder"] is None
    assert cfg["current_image"] is None
    assert cfg["interval_custom_seconds"] is None


def test_load_config_interval_custom_label_and_seconds_kept(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"interval": dv.CUSTOM_INTERVAL_LABEL, "interval_custom_seconds": 45}),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["interval"] == dv.CUSTOM_INTERVAL_LABEL
    assert cfg["interval_custom_seconds"] == 45


def test_load_config_folders_default_not_shared_after_invalid(tmp_path):
    """A rejected 'folders' field must not leave cfg['folders'] aliased to
    DEFAULT_CONFIG['folders'] — mutating it later would contaminate the
    shared default for the rest of the process."""
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"folders": "not-a-list"}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["folders"] == []
    cfg["folders"].append("D:\\Contaminated")
    assert dv.DEFAULT_CONFIG["folders"] == []


def test_load_config_custom_seconds_infinite_falls_back(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"interval_custom_seconds": float("inf")}), encoding="utf-8"
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["interval_custom_seconds"] is None


def test_load_config_custom_seconds_nan_falls_back(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"interval_custom_seconds": float("nan")}), encoding="utf-8"
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["interval_custom_seconds"] is None


def test_load_config_valid_values_kept(tmp_path):
    payload = {
        "folders": ["D:\\Wallpapers"],
        "current_folder": "D:\\Wallpapers",
        "current_image": "D:\\Wallpapers\\a.jpg",
        "style": "Centre",
        "interval": "1 hour",
        "shuffle": True,
        "interval_custom_seconds": None,
        "tray": {"enabled": False, "close_to_tray": False, "run_at_startup": True},
    }
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(payload), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg == {
        **payload,
        "playlists": [],
        "favourites": [],
        "hidden": [],
        "playback_source": None,
        "power": {"pause_on_battery_saver": True, "pause_on_fullscreen": True},
        "schedule": {"mode": "interval", "daily_times": []},
        "tags": {},
        "collections": [],
        "solar": {
            "enabled": False,
            "latitude": None,
            "longitude": None,
            "fallback_times": ["06:00", "08:00", "18:00", "21:00"],
        },
        "wallpaper_target": "spi",
        "hotkeys": {
            "enabled": True,
            "next": "Win+Alt+N",
            "prev": "Win+Alt+P",
            "favourite": "Win+Alt+L",
            "hide": "Win+Alt+H",
            "undo": "Win+Alt+Z",
            "toggle": "Win+Alt+S",
        },
        "ui": {
            "selected_page": "library",
            "appearance": "dark",
            "hud_always_visible": False,
            "reduced_motion": False,
            "seen_shortcut_notice_v2": False,
        },
    }


# ---------------------------------------------------------------------------
# tray config
# ---------------------------------------------------------------------------

def test_load_config_tray_defaults_when_missing(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"folders": ["/a"]}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["tray"] == {"enabled": True, "close_to_tray": True, "run_at_startup": False}


def test_load_config_tray_invalid_type_falls_back(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"tray": "not-a-dict"}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["tray"] == {"enabled": True, "close_to_tray": True, "run_at_startup": False}


def test_load_config_tray_partial_keys_filled(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"tray": {"enabled": False}}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["tray"] == {"enabled": False, "close_to_tray": True, "run_at_startup": False}


def test_load_config_tray_non_bool_values_fall_back(tmp_path):
    """bool(0) is False and bool("") is False, but neither is a *literal*
    boolean — a hand-edited or corrupted config with these values should
    fall back to the default rather than be silently coerced."""
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"tray": {"enabled": 0, "close_to_tray": "", "run_at_startup": 1}}),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["tray"] == {"enabled": True, "close_to_tray": True, "run_at_startup": False}


# ---------------------------------------------------------------------------
# Startup (Run key) — command building is pure; registry access is mocked
# ---------------------------------------------------------------------------

def test_build_startup_command_prefers_pythonw(tmp_path):
    python_exe = tmp_path / "python.exe"
    python_exe.write_bytes(b"")
    pythonw_exe = tmp_path / "pythonw.exe"
    pythonw_exe.write_bytes(b"")
    script = tmp_path / "desktop_vista.py"

    cmd = dv.build_startup_command(str(python_exe), str(script))

    assert str(pythonw_exe) in cmd
    assert str(script) in cmd
    assert "--minimized" in cmd


def test_build_startup_command_falls_back_without_pythonw(tmp_path):
    python_exe = tmp_path / "python.exe"
    python_exe.write_bytes(b"")
    script = tmp_path / "desktop_vista.py"

    cmd = dv.build_startup_command(str(python_exe), str(script))

    assert str(python_exe) in cmd
    assert "--minimized" in cmd


class _FakeRegKey:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _patch_fake_registry(monkeypatch, store: dict):
    """Redirect dv.winreg calls to an in-memory dict instead of the real registry."""
    monkeypatch.setattr(dv.winreg, "OpenKey", lambda *a, **k: _FakeRegKey())

    def fake_query(_key, name):
        if name not in store:
            raise FileNotFoundError(name)
        return store[name], 1

    def fake_set(_key, name, _reserved, _type, value):
        store[name] = value

    def fake_delete(_key, name):
        if name not in store:
            raise FileNotFoundError(name)
        del store[name]

    monkeypatch.setattr(dv.winreg, "QueryValueEx", fake_query)
    monkeypatch.setattr(dv.winreg, "SetValueEx", fake_set)
    monkeypatch.setattr(dv.winreg, "DeleteValue", fake_delete)


@pytest.mark.skipif(dv.winreg is None, reason="registry tests require Windows winreg")
def test_is_startup_enabled_false_when_absent(monkeypatch):
    _patch_fake_registry(monkeypatch, {})
    assert dv.is_startup_enabled() is False


@pytest.mark.skipif(dv.winreg is None, reason="registry tests require Windows winreg")
def test_set_startup_enabled_true_then_detected(monkeypatch):
    store: dict = {}
    _patch_fake_registry(monkeypatch, store)
    dv.set_startup_enabled(True)
    assert dv.STARTUP_VALUE_NAME in store
    assert "--minimized" in store[dv.STARTUP_VALUE_NAME]
    assert dv.is_startup_enabled() is True


@pytest.mark.skipif(dv.winreg is None, reason="registry tests require Windows winreg")
def test_set_startup_enabled_false_removes_entry(monkeypatch):
    store = {dv.STARTUP_VALUE_NAME: "existing command"}
    _patch_fake_registry(monkeypatch, store)
    dv.set_startup_enabled(False)
    assert dv.STARTUP_VALUE_NAME not in store
    assert dv.is_startup_enabled() is False


@pytest.mark.skipif(dv.winreg is None, reason="registry tests require Windows winreg")
def test_set_startup_enabled_false_when_already_absent_is_noop(monkeypatch):
    store: dict = {}
    _patch_fake_registry(monkeypatch, store)
    dv.set_startup_enabled(False)
    assert dv.STARTUP_VALUE_NAME not in store


# ---------------------------------------------------------------------------
# save_config (atomic)
# ---------------------------------------------------------------------------

def test_save_config_atomic_roundtrip(tmp_path):
    cfg_path = tmp_path / "config.json"
    data = {
        "folders": ["/tmp/pics"],
        "current_folder": "/tmp/pics",
        "current_image": None,
        "style": "Fit",
        "interval": "5 minutes",
        "shuffle": True,
    }
    dv.save_config(data, cfg_path)
    assert cfg_path.is_file()
    assert not cfg_path.with_suffix(".json.tmp").exists()
    # sibling .tmp from with_suffix(suffix + ".tmp")
    assert not Path(str(cfg_path) + ".tmp").exists()
    loaded = dv.load_config(cfg_path)
    assert loaded["folders"] == ["/tmp/pics"]
    assert loaded["style"] == "Fit"
    assert loaded["shuffle"] is True


def test_save_config_tmp_cleaned_on_success(tmp_path):
    cfg_path = tmp_path / "config.json"
    dv.save_config(dict(dv.DEFAULT_CONFIG), cfg_path)
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


# ---------------------------------------------------------------------------
# playback history ring (v1.6)
# ---------------------------------------------------------------------------

def test_load_history_missing_file_returns_empty(tmp_path):
    assert dv.load_history(tmp_path / "playback_state.json") == []


def test_save_history_atomic_roundtrip(tmp_path):
    state_path = tmp_path / "playback_state.json"
    dv.save_history(["C:\\A\\1.jpg", "C:\\A\\2.jpg"], state_path)
    assert state_path.is_file()
    assert not list(tmp_path.glob("*.tmp"))
    assert dv.load_history(state_path) == ["C:\\A\\1.jpg", "C:\\A\\2.jpg"]


def test_load_history_truncates_to_max(tmp_path):
    state_path = tmp_path / "playback_state.json"
    entries = [f"C:\\A\\{i}.jpg" for i in range(dv.HISTORY_MAX + 20)]
    state_path.write_text(json.dumps({"history": entries}), encoding="utf-8")
    loaded = dv.load_history(state_path)
    assert len(loaded) == dv.HISTORY_MAX
    assert loaded == entries[-dv.HISTORY_MAX:]


def test_load_history_malformed_file_returns_empty(tmp_path):
    state_path = tmp_path / "playback_state.json"
    state_path.write_text("not json", encoding="utf-8")
    assert dv.load_history(state_path) == []

    state_path.write_text(json.dumps({"history": "not-a-list"}), encoding="utf-8")
    assert dv.load_history(state_path) == []

    state_path.write_text(json.dumps({"history": [1, 2, 3]}), encoding="utf-8")
    assert dv.load_history(state_path) == []


# ---------------------------------------------------------------------------
# list_images
# ---------------------------------------------------------------------------

def test_list_images_sorting(tmp_path):
    names = ["c.PNG", "a.jpg", "b.webp", "readme.txt", "d.jpeg"]
    for n in names:
        (tmp_path / n).write_bytes(b"x")
    result = dv.list_images(str(tmp_path))
    assert result == [
        str(tmp_path / "a.jpg"),
        str(tmp_path / "b.webp"),
        str(tmp_path / "c.PNG"),
        str(tmp_path / "d.jpeg"),
    ]


def test_list_images_missing_path_returns_empty():
    assert dv.list_images("/nonexistent/path/desktop_vista_xyz") == []


def test_list_images_unreadable_returns_empty(tmp_path, monkeypatch):
    def boom(_self):
        raise OSError("drive offline")

    monkeypatch.setattr(Path, "iterdir", boom)
    assert dv.list_images(str(tmp_path)) == []


# ---------------------------------------------------------------------------
# Offline-aware folders
# ---------------------------------------------------------------------------

def test_is_folder_online_true_for_existing_dir(tmp_path):
    assert dv.is_folder_online(str(tmp_path)) is True


def test_is_folder_online_false_for_missing_dir(tmp_path):
    assert dv.is_folder_online(str(tmp_path / "nonexistent_xyz")) is False


def test_folder_display_label_online_unchanged(tmp_path):
    folder = str(tmp_path)
    assert dv.folder_display_label(folder) == folder


def test_folder_display_label_offline_badged(tmp_path):
    folder = str(tmp_path / "gone")
    assert dv.folder_display_label(folder) == folder + dv.OFFLINE_SUFFIX


def test_folder_display_label_uses_online_cache_not_filesystem(tmp_path):
    """v1.6: a recurring probe (the reconnect poll) must never fall back to
    a live filesystem check — an unreachable NAS path would block the Tk
    thread for the OS network timeout. A real (online) folder, if the cache
    says otherwise, must show as offline; an unknown folder defaults to
    online rather than pessimistically badging everything before the first
    probe completes."""
    real_folder = str(tmp_path)
    assert dv.folder_display_label(real_folder, {real_folder: False}) == (
        real_folder + dv.OFFLINE_SUFFIX
    )
    assert dv.folder_display_label(real_folder, {}) == real_folder
    assert dv.folder_display_label("D:\\Unknown", {}) == "D:\\Unknown"


def test_playlist_folder_status_uses_online_cache():
    playlist = {"folders": ["A", "B", "C"]}
    online, total = dv.playlist_folder_status(playlist, {"A": True, "B": False, "C": True})
    assert (online, total) == (2, 3)
    # Unlisted folders default to online, same as folder_display_label.
    online, total = dv.playlist_folder_status(playlist, {"A": False})
    assert (online, total) == (2, 3)


# ---------------------------------------------------------------------------
# v1.3 — playlists, favourites/hidden, playback_source
# ---------------------------------------------------------------------------

def test_dedupe_preserve_order():
    assert dv.dedupe_preserve_order(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]


def test_load_config_playlists_valid_kept(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {"playlists": [{"id": "p1", "name": "Workday", "folders": ["C:\\A", "D:\\B"]}]}
        ),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["playlists"] == [{"id": "p1", "name": "Workday", "folders": ["C:\\A", "D:\\B"]}]


def test_load_config_playlists_drops_malformed_entries(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "playlists": [
                    {"id": "p1", "name": "Good", "folders": ["C:\\A"]},
                    {"id": "p1", "name": "Duplicate id", "folders": []},  # dup id, dropped
                    {"name": "Missing id", "folders": []},
                    {"id": "p2", "name": "", "folders": []},  # blank name
                    {"id": "p3", "name": "Bad folders", "folders": [1, 2]},
                    "not-a-dict",
                ]
            }
        ),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["playlists"] == [{"id": "p1", "name": "Good", "folders": ["C:\\A"]}]


def test_load_config_favourites_hidden_kept_and_deduped(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"favourites": ["a.jpg", "b.jpg", "a.jpg"], "hidden": ["c.jpg"]}),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["favourites"] == ["a.jpg", "b.jpg"]
    assert cfg["hidden"] == ["c.jpg"]


def test_load_config_favourites_invalid_type_falls_back(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"favourites": "not-a-list"}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["favourites"] == []


def test_load_config_playback_source_valid_folder_kept(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {"folders": ["C:\\A"], "playback_source": {"kind": "folder", "id": "C:\\A"}}
        ),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["playback_source"] == {"kind": "folder", "id": "C:\\A"}


def test_load_config_playback_source_dangling_reference_falls_back(tmp_path):
    """A playback_source pointing at a folder that no longer exists in
    'folders' (e.g. removed since) must not be trusted verbatim."""
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"folders": [], "playback_source": {"kind": "folder", "id": "C:\\Gone"}}),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["playback_source"] is None


def test_load_config_playback_source_playlist_reference(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "playlists": [{"id": "p1", "name": "Workday", "folders": []}],
                "playback_source": {"kind": "playlist", "id": "p1"},
            }
        ),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["playback_source"] == {"kind": "playlist", "id": "p1"}


def test_load_config_playback_source_collection_reference(tmp_path):
    """v1.6 regression: a saved collection playback_source must survive a
    reload rather than being dropped by a kind-whitelist that only knew
    about folders and playlists (notes_005 §0 defect #4)."""
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "collections": [{"id": "c1", "name": "Dusk", "tags_any": ["dusk"]}],
                "playback_source": {"kind": "collection", "id": "c1"},
            }
        ),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["playback_source"] == {"kind": "collection", "id": "c1"}


def test_load_config_playback_source_dangling_collection_falls_back(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"collections": [], "playback_source": {"kind": "collection", "id": "gone"}}),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["playback_source"] is None


def test_resolve_source_images_playlist_unions_folders(tmp_path):
    f1, f2 = tmp_path / "f1", tmp_path / "f2"
    f1.mkdir()
    f2.mkdir()
    (f1 / "a.jpg").write_bytes(b"x")
    (f2 / "b.jpg").write_bytes(b"x")
    cfg = {
        "playlists": [{"id": "p1", "name": "Both", "folders": [str(f1), str(f2)]}],
        "hidden": [],
    }
    images = dv.resolve_source_images(cfg, "playlist", "p1")
    assert images == [str(f1 / "a.jpg"), str(f2 / "b.jpg")]


def test_resolve_source_images_filters_hidden(tmp_path):
    folder = tmp_path
    (folder / "a.jpg").write_bytes(b"x")
    (folder / "b.jpg").write_bytes(b"x")
    cfg = {"hidden": [str(folder / "b.jpg")]}
    images = dv.resolve_source_images(cfg, "folder", str(folder))
    assert images == [str(folder / "a.jpg")]


def test_resolve_source_images_missing_playlist_returns_empty():
    assert dv.resolve_source_images({"playlists": [], "hidden": []}, "playlist", "gone") == []


# ---------------------------------------------------------------------------
# join_monitor_topology (notes_007 §1.3 — read-only session join)
# ---------------------------------------------------------------------------

def test_join_monitor_topology_two_monitor_exact_match():
    gdi = [
        {"rect": (0, 0, 1920, 1080), "primary": True},
        {"rect": (1920, 0, 3840, 1080), "primary": False},
    ]
    com = [
        ("com-a", (0, 0, 1920, 1080)),
        ("com-b", (1920, 0, 3840, 1080)),
    ]
    assert dv.join_monitor_topology(gdi, com) == [0, 1]


def test_join_monitor_topology_negative_origin():
    # A monitor placed to the left of the primary has negative coordinates.
    gdi = [
        {"rect": (-1920, 0, 0, 1080), "primary": False},
        {"rect": (0, 0, 1920, 1080), "primary": True},
    ]
    com = [
        ("com-a", (0, 0, 1920, 1080)),
        ("com-b", (-1920, 0, 0, 1080)),
    ]
    assert dv.join_monitor_topology(gdi, com) == [1, 0]


def test_join_monitor_topology_clone_is_unresolved():
    # Two COM entries reporting the identical RECT (clone mode) must tie,
    # never be guessed — a wrong guess here would assign wallpaper to the
    # wrong physical output once v2.0 wires an apply target off this join.
    gdi = [{"rect": (0, 0, 1920, 1080), "primary": True}]
    com = [
        ("com-a", (0, 0, 1920, 1080)),
        ("com-b", (0, 0, 1920, 1080)),
    ]
    assert dv.join_monitor_topology(gdi, com) == [None]


def test_join_monitor_topology_no_overlap_is_unresolved():
    gdi = [{"rect": (0, 0, 1920, 1080), "primary": True}]
    com = [("com-a", (5000, 5000, 6000, 6000))]
    assert dv.join_monitor_topology(gdi, com) == [None]


def test_join_monitor_topology_empty_com_list():
    gdi = [{"rect": (0, 0, 1920, 1080), "primary": True}]
    assert dv.join_monitor_topology(gdi, []) == [None]


# ---------------------------------------------------------------------------
# resolve_rebuilt_index (notes_007 §1.2 — Hidden Items playback invariants)
# ---------------------------------------------------------------------------

def test_resolve_rebuilt_index_prefers_preferred_path():
    images = ["a.jpg", "b.jpg", "c.jpg"]
    assert dv.resolve_rebuilt_index(images, old_index=0, preferred_path="c.jpg") == 2


def test_resolve_rebuilt_index_clamps_when_list_shrinks():
    # Old index pointed past the end of a list that just lost its last item.
    assert dv.resolve_rebuilt_index(["a.jpg", "b.jpg"], old_index=2, preferred_path=None) == 1


def test_resolve_rebuilt_index_empty_list_is_negative_one():
    assert dv.resolve_rebuilt_index([], old_index=0, preferred_path=None) == -1
    assert dv.resolve_rebuilt_index([], old_index=0, preferred_path="gone.jpg") == -1


def test_resolve_rebuilt_index_preferred_path_absent_falls_back_to_clamp():
    assert dv.resolve_rebuilt_index(["a.jpg"], old_index=5, preferred_path="not-there.jpg") == 0


def test_hide_current_image_shrinks_list_clamps_index_and_empties_shuffle_deck(tmp_path):
    """Reproduces _rebuild_playback_after_filter_change's contract: hiding
    the last image in a folder must not leave a stale shuffle deck that can
    later IndexError or point at the hidden file."""
    folder = tmp_path
    for name in ("a.jpg", "b.jpg", "c.jpg"):
        (folder / name).write_bytes(b"x")
    cfg = {"hidden": []}
    images = dv.resolve_source_images(cfg, "folder", str(folder))
    old_index = len(images) - 1  # currently viewing the last image
    hidden_path = images[old_index]

    dv.set_membership(cfg, "hidden", hidden_path, True)
    new_images = dv.resolve_source_images(cfg, "folder", str(folder))
    new_index = dv.resolve_rebuilt_index(new_images, old_index, preferred_path=None)
    # Deck reset is the caller's job (self._shuffle_order = []); the deck
    # itself is only valid for the list it was built against.
    shuffle_order: list[int] = []

    assert hidden_path not in new_images
    assert len(new_images) == 2
    assert 0 <= new_index < len(new_images)
    assert shuffle_order == []


def test_hide_then_rebuild_shuffle_deck_never_indexes_hidden_path(tmp_path):
    folder = tmp_path
    for name in ("a.jpg", "b.jpg", "c.jpg", "d.jpg"):
        (folder / name).write_bytes(b"x")
    cfg = {"hidden": []}
    images = dv.resolve_source_images(cfg, "folder", str(folder))
    hidden_path = images[1]

    dv.set_membership(cfg, "hidden", hidden_path, True)
    new_images = dv.resolve_source_images(cfg, "folder", str(folder))
    new_index = dv.resolve_rebuilt_index(new_images, old_index=1, preferred_path=None)
    # A freshly-reset deck (as _rebuild_playback_after_filter_change leaves
    # it) forces the next _advance_shuffle call to rebuild against the new,
    # correct length rather than reuse indices from the old one.
    deck = dv.build_shuffle_deck(len(new_images), new_index)

    assert sorted(deck) == list(range(len(new_images)))
    assert all(new_images[i] != hidden_path for i in deck)


def test_unhide_only_image_restores_preview_at_index_zero(tmp_path):
    folder = tmp_path
    (folder / "only.jpg").write_bytes(b"x")
    only_path = str(folder / "only.jpg")
    cfg = {"hidden": [only_path], "favourites": []}

    assert dv.resolve_source_images(cfg, "folder", str(folder)) == []

    dv.set_membership(cfg, "hidden", only_path, False)
    images = dv.resolve_source_images(cfg, "folder", str(folder))
    index = dv.resolve_rebuilt_index(images, old_index=-1, preferred_path=only_path)

    assert images == [only_path]
    assert index == 0
    assert cfg["favourites"] == []  # unhide must not touch favourites


# ---------------------------------------------------------------------------
# collection_match_count (notes_007 §1.1 — collection editor live count)
# ---------------------------------------------------------------------------

def test_collection_match_count_empty_tags_is_zero():
    assert dv.collection_match_count({"folders": [], "tags": {}}, []) == 0


def test_collection_match_count_matches_resolve_source_images(tmp_path):
    folder = tmp_path
    (folder / "a.jpg").write_bytes(b"x")
    (folder / "b.jpg").write_bytes(b"x")
    cfg = {
        "folders": [str(folder)],
        "playlists": [],
        "hidden": [],
        "tags": {str(folder / "a.jpg"): ["nature"]},
    }
    assert dv.collection_match_count(cfg, ["nature"]) == 1
    assert dv.collection_match_count(cfg, ["not-a-real-tag"]) == 0


def test_collection_match_count_does_not_mutate_cfg_collections(tmp_path):
    cfg = {"folders": [], "playlists": [], "hidden": [], "tags": {}, "collections": []}
    dv.collection_match_count(cfg, ["nature"])
    assert cfg["collections"] == []  # the draft snapshot must not leak into real cfg


def test_about_copy_has_rights_and_owner_no_local_paths():
    joined = "\n".join(dv.ABOUT_COPY)
    assert "All rights reserved" in joined
    assert "Mark Hawksworth" in joined
    assert "hawkers63" in joined
    assert "\\" not in joined  # no leaked source-file or wallpaper folder paths
    assert str(dv.APP_DIR) not in joined


def test_set_membership_add_and_remove():
    cfg = {"favourites": ["a.jpg"]}
    dv.set_membership(cfg, "favourites", "b.jpg", True)
    assert cfg["favourites"] == ["a.jpg", "b.jpg"]
    dv.set_membership(cfg, "favourites", "a.jpg", False)
    assert cfg["favourites"] == ["b.jpg"]
    # Removing a non-member, or adding an existing member, is a no-op.
    dv.set_membership(cfg, "favourites", "z.jpg", False)
    assert cfg["favourites"] == ["b.jpg"]
    dv.set_membership(cfg, "favourites", "b.jpg", True)
    assert cfg["favourites"] == ["b.jpg"]


def test_source_display_label_playlist_all_online(tmp_path):
    (tmp_path / "sub").mkdir()
    cfg = {"playlists": [{"id": "p1", "name": "Workday", "folders": [str(tmp_path / "sub")]}]}
    assert dv.source_display_label(cfg, "playlist", "p1") == "▶ Workday"


def test_source_display_label_playlist_partial_offline():
    cfg = {
        "playlists": [
            {"id": "p1", "name": "Workday", "folders": ["C:\\gone1", "C:\\gone2"]}
        ]
    }
    assert dv.source_display_label(cfg, "playlist", "p1") == "▶ Workday  (0/2 drives online)"


# ---------------------------------------------------------------------------
# v1.4 — power/fullscreen predicates, daily schedule math
# ---------------------------------------------------------------------------

def test_load_config_power_defaults_when_missing(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["power"] == {"pause_on_battery_saver": True, "pause_on_fullscreen": True}
    assert cfg["schedule"] == {"mode": "interval", "daily_times": []}


def test_load_config_power_non_bool_falls_back(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"power": {"pause_on_battery_saver": "yes", "pause_on_fullscreen": 0}}),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["power"] == {"pause_on_battery_saver": True, "pause_on_fullscreen": True}


def test_load_config_schedule_daily_times_filters_invalid(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {"schedule": {"mode": "daily", "daily_times": ["08:00", "25:00", "9:5", "18:30"]}}
        ),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["schedule"] == {"mode": "daily", "daily_times": ["08:00", "18:30"]}


def test_load_config_schedule_invalid_mode_falls_back(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"schedule": {"mode": "lunar"}}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["schedule"]["mode"] == "interval"


def test_load_config_schedule_solar_mode_kept(tmp_path):
    """v1.6: 'solar' is now a valid schedule.mode alongside interval/daily —
    see notes_005 §2.2.1 and _solar_advance/_compute_next_due."""
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"schedule": {"mode": "solar"}}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["schedule"]["mode"] == "solar"


def test_load_config_hotkeys_defaults_when_missing(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["hotkeys"] == dv.DEFAULT_CONFIG["hotkeys"]


def test_load_config_hotkeys_per_binding_fallback(tmp_path):
    """An individual malformed binding falls back to just that action's
    default, not the whole hotkeys block — matches the pattern used for
    tray flags and power settings."""
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "hotkeys": {
                    "enabled": False,
                    "next": "N",  # no modifier — invalid, must fall back
                    "prev": "Ctrl+Alt+P",  # valid, non-default — must be kept
                }
            }
        ),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["hotkeys"]["enabled"] is False
    assert cfg["hotkeys"]["next"] == "Win+Alt+N"
    assert cfg["hotkeys"]["prev"] == "Ctrl+Alt+P"
    assert cfg["hotkeys"]["undo"] == "Win+Alt+Z"


def test_load_config_hotkeys_invalid_block_falls_back(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"hotkeys": "not-a-dict"}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["hotkeys"] == dv.DEFAULT_CONFIG["hotkeys"]


def test_load_config_ui_defaults_when_missing(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["ui"] == dv.DEFAULT_CONFIG["ui"]


def test_load_config_ui_valid_values_kept(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {"ui": {"selected_page": "displays", "appearance": "light", "hud_always_visible": True}}
        ),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["ui"]["selected_page"] == "displays"
    assert cfg["ui"]["appearance"] == "light"
    assert cfg["ui"]["hud_always_visible"] is True
    assert cfg["ui"]["reduced_motion"] is False  # untouched key keeps its default


def test_load_config_ui_invalid_values_fall_back(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"ui": {"selected_page": "nowhere", "appearance": "purple", "reduced_motion": "yes"}}),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["ui"]["selected_page"] == "library"
    assert cfg["ui"]["appearance"] == "dark"
    assert cfg["ui"]["reduced_motion"] is False


def test_load_config_ui_invalid_block_falls_back(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"ui": "not-a-dict"}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["ui"] == dv.DEFAULT_CONFIG["ui"]


def test_is_valid_time_string():
    assert dv.is_valid_time_string("08:00") is True
    assert dv.is_valid_time_string("23:59") is True
    assert dv.is_valid_time_string("24:00") is False
    assert dv.is_valid_time_string("8:00") is False
    assert dv.is_valid_time_string("08:60") is False
    assert dv.is_valid_time_string("not-a-time") is False


def test_next_daily_trigger_picks_soonest_today():
    now = datetime(2026, 9, 9, 10, 0, 0)
    trigger = dv.next_daily_trigger(now, ["08:00", "14:00", "20:00"])
    assert trigger == datetime(2026, 9, 9, 14, 0, 0)


def test_next_daily_trigger_rolls_to_tomorrow_when_all_passed():
    now = datetime(2026, 9, 9, 22, 0, 0)
    trigger = dv.next_daily_trigger(now, ["08:00", "14:00"])
    assert trigger == datetime(2026, 9, 10, 8, 0, 0)


def test_next_daily_trigger_no_valid_times_returns_none():
    now = datetime(2026, 9, 9, 10, 0, 0)
    assert dv.next_daily_trigger(now, []) is None
    assert dv.next_daily_trigger(now, ["bogus"]) is None


def test_next_daily_trigger_exact_time_rolls_to_tomorrow():
    """A candidate exactly equal to 'now' has already happened this tick,
    so it must roll forward rather than fire again immediately."""
    now = datetime(2026, 9, 9, 8, 0, 0)
    trigger = dv.next_daily_trigger(now, ["08:00"])
    assert trigger == datetime(2026, 9, 10, 8, 0, 0)


def test_is_battery_saver_active_pure_predicate():
    assert dv.is_battery_saver_active({"battery_saver_on": True}) is True
    assert dv.is_battery_saver_active({"battery_saver_on": False}) is False
    assert dv.is_battery_saver_active(None) in (True, False)  # falls back to live query, not a crash


def test_is_fullscreen_active_pure_predicate():
    assert dv.is_fullscreen_active(3) is True  # QUNS_RUNNING_D3D_FULL_SCREEN
    assert dv.is_fullscreen_active(4) is True  # QUNS_PRESENTATION_MODE
    assert dv.is_fullscreen_active(5) is False  # QUNS_ACCEPTS_NOTIFICATIONS
    assert dv.is_fullscreen_active(None) is False


# ---------------------------------------------------------------------------
# v1.5 — tags/collections, solar data model, monitor topology math
# ---------------------------------------------------------------------------

def test_get_set_tags_roundtrip():
    # Tags are case-sensitive and deduped only on exact match, with
    # whitespace trimmed — "Nature" and "nature" are distinct tags.
    cfg = {"tags": {}}
    dv.set_tags(cfg, "a.jpg", ["Nature", "  minimal ", "Nature"])
    assert dv.get_tags(cfg, "a.jpg") == ["Nature", "minimal"]


def test_set_tags_empty_list_removes_entry():
    cfg = {"tags": {"a.jpg": ["x"]}}
    dv.set_tags(cfg, "a.jpg", [])
    assert dv.get_tags(cfg, "a.jpg") == []
    assert "a.jpg" not in cfg["tags"]


def test_load_config_collections_valid_kept(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"collections": [{"id": "c1", "name": "Nature", "tags_any": ["nature"]}]}),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["collections"] == [{"id": "c1", "name": "Nature", "tags_any": ["nature"]}]


def test_load_config_collections_drops_malformed(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "collections": [
                    {"id": "c1", "name": "Good", "tags_any": ["x"]},
                    {"id": "c2", "name": "No tags", "tags_any": []},
                    {"id": "", "name": "Blank id", "tags_any": ["x"]},
                ]
            }
        ),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["collections"] == [{"id": "c1", "name": "Good", "tags_any": ["x"]}]


def test_resolve_collection_candidate_images_matches_by_tag(tmp_path):
    folder = tmp_path
    (folder / "a.jpg").write_bytes(b"x")
    (folder / "b.jpg").write_bytes(b"x")
    cfg = {
        "folders": [str(folder)],
        "playlists": [],
        "tags": {str(folder / "a.jpg"): ["nature"]},
        "collections": [{"id": "c1", "name": "Nature", "tags_any": ["nature"]}],
    }
    assert dv.resolve_source_images(cfg, "collection", "c1") == [str(folder / "a.jpg")]


def test_resolve_collection_candidate_images_missing_collection_empty():
    cfg = {"folders": [], "playlists": [], "tags": {}, "collections": []}
    assert dv.resolve_source_images(cfg, "collection", "gone") == []


def test_source_display_label_collection():
    cfg = {"collections": [{"id": "c1", "name": "Nature", "tags_any": ["nature"]}]}
    assert dv.source_display_label(cfg, "collection", "c1") == "# Nature"


def test_load_config_solar_defaults_when_missing(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["solar"] == {
        "enabled": False, "latitude": None, "longitude": None,
        "fallback_times": ["06:00", "08:00", "18:00", "21:00"],
    }


def test_load_config_solar_valid_coordinates_kept(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"solar": {"enabled": True, "latitude": 51.5, "longitude": -0.1}}),
        encoding="utf-8",
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["solar"]["enabled"] is True
    assert cfg["solar"]["latitude"] == 51.5
    assert cfg["solar"]["longitude"] == -0.1


def test_load_config_solar_out_of_range_coordinates_rejected(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"solar": {"latitude": 999, "longitude": float("nan")}}), encoding="utf-8"
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["solar"]["latitude"] is None
    assert cfg["solar"]["longitude"] is None


def test_load_config_solar_bad_fallback_times_falls_back_to_default(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps({"solar": {"fallback_times": ["08:00"]}}), encoding="utf-8"  # only 1, need 4
    )
    cfg = dv.load_config(cfg_path)
    assert cfg["solar"]["fallback_times"] == ["06:00", "08:00", "18:00", "21:00"]


def test_enumerate_monitors_returns_list_type():
    # Real hardware-dependent; just assert the contract (list, never raises).
    result = dv.enumerate_monitors()
    assert isinstance(result, list)


def test_compute_topology_layout_single_monitor_fills_box():
    monitors = [{"device": "M1", "rect": (0, 0, 1920, 1080), "primary": True}]
    layout = dv.compute_topology_layout(monitors, 200, 100)
    assert len(layout) == 1
    box = layout[0]["layout"]
    assert box["x"] == 0 and box["y"] == 0
    assert box["w"] <= 200 and box["h"] <= 100


def test_compute_topology_layout_two_monitors_relative_position():
    # Monitor 2 sits to the right of monitor 1 — layout must preserve that.
    monitors = [
        {"device": "M1", "rect": (0, 0, 1920, 1080), "primary": True},
        {"device": "M2", "rect": (1920, 0, 3840, 1080), "primary": False},
    ]
    layout = dv.compute_topology_layout(monitors, 400, 100)
    assert layout[0]["layout"]["x"] < layout[1]["layout"]["x"]


def test_compute_topology_layout_empty_returns_empty():
    assert dv.compute_topology_layout([], 200, 100) == []


def test_compute_topology_layout_negative_coordinates_handled():
    """A monitor positioned left of/above the primary (negative coords)
    must still map into non-negative box-local pixels."""
    monitors = [
        {"device": "M1", "rect": (0, 0, 1920, 1080), "primary": True},
        {"device": "M2", "rect": (-1920, 0, 0, 1080), "primary": False},
    ]
    layout = dv.compute_topology_layout(monitors, 400, 100)
    assert all(m["layout"]["x"] >= 0 and m["layout"]["y"] >= 0 for m in layout)
    assert layout[1]["layout"]["x"] < layout[0]["layout"]["x"]


# ---------------------------------------------------------------------------
# v2.0 experimental — wallpaper_target flag, COM backend module
# ---------------------------------------------------------------------------

def test_load_config_wallpaper_target_defaults_to_spi(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["wallpaper_target"] == "spi"


def test_load_config_wallpaper_target_invalid_falls_back_to_spi(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"wallpaper_target": "gpu-shader"}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["wallpaper_target"] == "spi"


def test_load_config_wallpaper_target_com_kept(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"wallpaper_target": "com"}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["wallpaper_target"] == "com"


@pytest.mark.skipif(dv.windows_wallpaper_com is None, reason="requires comtypes on Windows")
def test_com_position_values_cover_all_fit_styles():
    import windows_wallpaper_com as wc
    # Every style Desktop Vista's UI offers must map to a real position enum
    # value, or the "com" target would silently fall back to Fill for it.
    for style in dv.WALLPAPER_STYLES:
        assert style in wc.POSITION_VALUES


@pytest.mark.skipif(dv.windows_wallpaper_com is None, reason="requires comtypes on Windows")
def test_com_backend_rejects_span_for_specific_monitor():
    import windows_wallpaper_com as wc
    with pytest.raises(wc.ComWallpaperError):
        wc.ComWallpaperBackend._set_wallpaper_sta("some-device-id", "C:\\x.jpg", "Span")


# ---------------------------------------------------------------------------
# Custom slideshow interval resolution
# ---------------------------------------------------------------------------

def test_resolve_interval_seconds_known_label():
    assert dv.resolve_interval_seconds("1 hour", None) == 3600


def test_resolve_interval_seconds_unknown_label_falls_back():
    assert dv.resolve_interval_seconds("bogus", None) == dv.SLIDESHOW_INTERVALS["15 minutes"]


def test_resolve_interval_seconds_custom_valid():
    assert dv.resolve_interval_seconds(dv.CUSTOM_INTERVAL_LABEL, 42) == 42


def test_resolve_interval_seconds_custom_below_minimum_clamped():
    assert dv.resolve_interval_seconds(dv.CUSTOM_INTERVAL_LABEL, 1) == dv.MIN_CUSTOM_INTERVAL_SECONDS


def test_resolve_interval_seconds_custom_missing_falls_back():
    assert dv.resolve_interval_seconds(dv.CUSTOM_INTERVAL_LABEL, None) == \
        dv.SLIDESHOW_INTERVALS["15 minutes"]


def test_resolve_interval_seconds_custom_invalid_type_falls_back():
    assert dv.resolve_interval_seconds(dv.CUSTOM_INTERVAL_LABEL, "abc") == \
        dv.SLIDESHOW_INTERVALS["15 minutes"]


# ---------------------------------------------------------------------------
# WebP / non-native transcode cache
# ---------------------------------------------------------------------------

def test_ensure_wallpaper_native_passthrough(tmp_path):
    img = tmp_path / "photo.jpg"
    Image.new("RGB", (32, 32), color=(10, 20, 30)).save(img, format="JPEG")
    assert dv.ensure_wallpaper_path(str(img), cache_root=tmp_path / "cache") == str(img)


def test_ensure_wallpaper_webp_creates_cache(tmp_path):
    src = tmp_path / "shot.webp"
    Image.new("RGB", (40, 24), color=(200, 100, 50)).save(src, format="WEBP")
    cache = tmp_path / "cache"
    out = dv.ensure_wallpaper_path(str(src), cache_root=cache)
    out_path = Path(out)
    assert out_path.suffix.lower() == ".jpg"
    assert out_path.is_file()
    assert cache in out_path.parents or out_path.parent == cache
    # Second call should reuse cached file (same path)
    out2 = dv.ensure_wallpaper_path(str(src), cache_root=cache)
    assert out2 == out


def test_ensure_wallpaper_png_passthrough(tmp_path):
    img = tmp_path / "tile.png"
    Image.new("RGB", (8, 8), color=(1, 2, 3)).save(img, format="PNG")
    assert dv.ensure_wallpaper_path(str(img), cache_root=tmp_path / "c") == str(img)


# ---------------------------------------------------------------------------
# Fisher–Yates shuffle deck
# ---------------------------------------------------------------------------

def test_build_shuffle_deck_all_indices_once(monkeypatch):
    # Deterministic but still a permutation
    seq = iter([0, 0, 0, 0, 0, 0, 0, 0, 0])  # always swap with 0 -> reverse-ish
    monkeypatch.setattr(dv.random, "randint", lambda a, b: next(seq, a))

    n = 5
    deck = dv.build_shuffle_deck(n, current=-1)
    assert sorted(deck) == list(range(n))
    assert len(deck) == n


def test_build_shuffle_deck_skips_current_first(monkeypatch):
    # Force a shuffle that would start with current=2, then verify skip.
    # Make randint always return 0 so Fisher–Yates produces a known order,
    # then assert skip-current behaviour separately with a crafted case.

    def always_zero(a, b):
        return a  # no-op swaps effectively leave [0,1,...,n-1] if j=i... wait

    # Simpler: call many times and ensure first != current when n>1
    monkeypatch.setattr(dv.random, "randint", lambda a, b: a)  # j=a=i -> identity
    deck = dv.build_shuffle_deck(4, current=0)
    # Identity shuffle starts with 0 == current, so should rotate current to end
    assert deck[0] != 0
    assert sorted(deck) == [0, 1, 2, 3]
    assert deck[-1] == 0


def test_build_shuffle_deck_empty_and_single():
    assert dv.build_shuffle_deck(0) == []
    assert dv.build_shuffle_deck(1) == [0]


def test_shuffle_deck_full_cycle_coverage():
    """Deplete a deck then rebuild; every index appears once per cycle."""
    n = 7
    current = 3
    seen_cycles = []
    deck = dv.build_shuffle_deck(n, current)
    assert sorted(deck) == list(range(n))
    assert deck[0] != current or n == 1
    seen_cycles.append(list(deck))
    # Second cycle after deplete
    deck2 = dv.build_shuffle_deck(n, deck[-1] if deck else -1)
    assert sorted(deck2) == list(range(n))


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def test_human_size():
    assert dv.human_size(500) == "500 B"
    assert "KB" in dv.human_size(2048)


def test_wallpaper_cache_key_stable(tmp_path):
    p = tmp_path / "x.jpg"
    p.write_bytes(b"abc")
    k1 = dv.wallpaper_cache_key(p)
    k2 = dv.wallpaper_cache_key(p)
    assert k1 == k2
    assert len(k1) == 32


# ---------------------------------------------------------------------------
# EXIF-rotated preview decoding
# ---------------------------------------------------------------------------

def test_load_preview_image_reports_rotated_dimensions(tmp_path):
    """A 100x50 source tagged EXIF orientation 6 (rotate 90) should be
    reported as displaying at 50x100 — dimensions swapped for the rotation
    — exercising the orientation-aware draft-box path."""
    path = tmp_path / "rotated.jpg"
    img = Image.new("RGB", (100, 50), color=(200, 50, 50))
    exif = img.getexif()
    exif[274] = 6  # Orientation tag
    img.save(path, format="JPEG", exif=exif)

    out, width, height = dv._load_preview_image(str(path), 200, 200)
    assert (width, height) == (50, 100)
    assert out.mode == "RGB"


def test_load_preview_image_unrotated_dimensions_unchanged(tmp_path):
    path = tmp_path / "normal.jpg"
    Image.new("RGB", (100, 50), color=(50, 200, 50)).save(path, format="JPEG")

    out, width, height = dv._load_preview_image(str(path), 200, 200)
    assert (width, height) == (100, 50)


# ---------------------------------------------------------------------------
# Tray icon image
# ---------------------------------------------------------------------------

def test_build_tray_icon_image_default_size():
    img = dv.build_tray_icon_image()
    assert img.size == (64, 64)
    assert img.mode == "RGBA"


def test_build_tray_icon_image_custom_size():
    img = dv.build_tray_icon_image(32)
    assert img.size == (32, 32)


def test_load_brand_icon_uses_shipped_asset():
    img = dv.load_brand_icon(64)
    assert img.mode == "RGBA"
    assert max(img.size) <= 64


def test_load_brand_icon_falls_back_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(dv, "BRAND_ICON_PATH", tmp_path / "does-not-exist.ico")
    img = dv.load_brand_icon(48)
    assert img.size == (48, 48)


# ---------------------------------------------------------------------------
# Startup staleness (registry command drift)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(dv.winreg is None, reason="registry tests require Windows winreg")
def test_is_startup_enabled_false_when_command_is_stale(monkeypatch):
    store = {dv.STARTUP_VALUE_NAME: '"C:\\old\\python.exe" "C:\\old\\desktop_vista.py" --minimized'}
    _patch_fake_registry(monkeypatch, store)
    assert dv.is_startup_enabled() is False
