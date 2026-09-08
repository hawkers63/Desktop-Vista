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


def test_load_config_valid_values_kept(tmp_path):
    payload = {
        "folders": ["D:\\Wallpapers"],
        "current_folder": "D:\\Wallpapers",
        "current_image": "D:\\Wallpapers\\a.jpg",
        "style": "Centre",
        "interval": "1 hour",
        "shuffle": True,
        "tray": {"enabled": False, "close_to_tray": False},
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
    assert cfg["tray"] == {"enabled": True, "close_to_tray": True}


def test_load_config_tray_invalid_type_falls_back(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"tray": "not-a-dict"}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["tray"] == {"enabled": True, "close_to_tray": True}


def test_load_config_tray_partial_keys_filled(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"tray": {"enabled": False}}), encoding="utf-8")
    cfg = dv.load_config(cfg_path)
    assert cfg["tray"] == {"enabled": False, "close_to_tray": True}


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
# Tray icon image
# ---------------------------------------------------------------------------

def test_build_tray_icon_image_default_size():
    img = dv.build_tray_icon_image()
    assert img.size == (64, 64)
    assert img.mode == "RGBA"


def test_build_tray_icon_image_custom_size():
    img = dv.build_tray_icon_image(32)
    assert img.size == (32, 32)
