# Copyright (c) 2026 hawkers63. All Rights Reserved.
"""Unit tests for Desktop Vista helpers (no display / Tk required)."""

from __future__ import annotations

import json
import os
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
    assert cfg == payload


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
