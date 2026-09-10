# Copyright (c) 2026 hawkers63. All Rights Reserved.
"""Unit + live-integration tests for hotkeys.py (global RegisterHotKey bindings)."""

from __future__ import annotations

import ctypes
import sys
import time

import pytest

import hotkeys as hk

WINDOWS_ONLY = pytest.mark.skipif(sys.platform != "win32", reason="ctypes Win32 APIs only")


# ---------------------------------------------------------------------------
# parse_binding / format_binding — pure, run everywhere
# ---------------------------------------------------------------------------

def test_parse_binding_default_set():
    assert hk.parse_binding("Win+Alt+N") == (hk.MOD_WIN | hk.MOD_ALT | hk.MOD_NOREPEAT, ord("N"))
    assert hk.parse_binding("Win+Alt+P") == (hk.MOD_WIN | hk.MOD_ALT | hk.MOD_NOREPEAT, ord("P"))


def test_parse_binding_case_and_whitespace_insensitive():
    assert hk.parse_binding(" win + alt + n ") == hk.parse_binding("Win+Alt+N")


def test_parse_binding_requires_a_modifier():
    # A bare key would steal normal typing — must be rejected.
    assert hk.parse_binding("N") is None


def test_parse_binding_rejects_unknown_modifier():
    assert hk.parse_binding("Super+N") is None


def test_parse_binding_rejects_unsupported_key():
    assert hk.parse_binding("Win+Alt+F1") is None
    assert hk.parse_binding("Win+Alt+") is None


def test_parse_binding_digit_key():
    mods, vk = hk.parse_binding("Ctrl+Shift+5")
    assert vk == ord("5")
    assert mods & hk.MOD_CONTROL and mods & hk.MOD_SHIFT


def test_format_binding_roundtrip_readable():
    mods, vk = hk.parse_binding("Win+Alt+N")
    assert hk.format_binding(mods, vk) == "Win+Alt+N"


# ---------------------------------------------------------------------------
# HotkeyListener — live, Windows only (this dev/test machine is win32)
# ---------------------------------------------------------------------------

@WINDOWS_ONLY
def test_listener_registers_and_fires():
    mods, vk = hk.parse_binding("Ctrl+Alt+Shift+9")  # unlikely to collide with anything real
    fired = []
    listener = hk.HotkeyListener([(1, mods, vk)], on_hotkey=fired.append)
    listener.start()
    try:
        assert listener.ready.wait(timeout=2.0)
        assert listener.conflicts == []

        user32 = ctypes.windll.user32
        user32.keybd_event(0x11, 0, 0, 0)  # VK_CONTROL down
        user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU (Alt) down
        user32.keybd_event(0x10, 0, 0, 0)  # VK_SHIFT down
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP
        user32.keybd_event(0x10, 0, 2, 0)
        user32.keybd_event(0x12, 0, 2, 0)
        user32.keybd_event(0x11, 0, 2, 0)

        deadline = time.monotonic() + 2.0
        while not fired and time.monotonic() < deadline:
            time.sleep(0.05)
        assert fired == [1]
    finally:
        listener.stop()
        listener.join(timeout=2.0)


@WINDOWS_ONLY
def test_listener_reports_conflict_without_retry():
    mods, vk = hk.parse_binding("Ctrl+Alt+Shift+8")
    first = hk.HotkeyListener([(1, mods, vk)], on_hotkey=lambda hid: None)
    first.start()
    try:
        assert first.ready.wait(timeout=2.0)
        assert first.conflicts == []

        second = hk.HotkeyListener([(1, mods, vk)], on_hotkey=lambda hid: None)
        second.start()
        try:
            assert second.ready.wait(timeout=2.0)
            assert second.conflicts == [hk.format_binding(mods & ~hk.MOD_NOREPEAT, vk)]
        finally:
            second.stop()
            second.join(timeout=2.0)
    finally:
        first.stop()
        first.join(timeout=2.0)


@WINDOWS_ONLY
def test_listener_unregisters_on_stop():
    mods, vk = hk.parse_binding("Ctrl+Alt+Shift+7")
    first = hk.HotkeyListener([(1, mods, vk)], on_hotkey=lambda hid: None)
    first.start()
    assert first.ready.wait(timeout=2.0)
    first.stop()
    first.join(timeout=2.0)

    # Now that the first listener has cleanly unregistered, the same
    # binding must be free for a second listener to claim.
    second = hk.HotkeyListener([(1, mods, vk)], on_hotkey=lambda hid: None)
    second.start()
    try:
        assert second.ready.wait(timeout=2.0)
        assert second.conflicts == []
    finally:
        second.stop()
        second.join(timeout=2.0)
