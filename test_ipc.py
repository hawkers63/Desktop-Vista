# Copyright (c) 2026 hawkers63. All Rights Reserved.
"""Unit + live-integration tests for ipc.py (single-instance mutex + named-pipe IPC)."""

from __future__ import annotations

import sys
import time

import pytest

import ipc

WINDOWS_ONLY = pytest.mark.skipif(sys.platform != "win32", reason="ctypes Win32 APIs only")


# ---------------------------------------------------------------------------
# cli_payload — pure, runs everywhere
# ---------------------------------------------------------------------------

def test_cli_payload_no_flags_returns_none():
    assert ipc.cli_payload([]) is None
    assert ipc.cli_payload(["--minimized"]) is None


@pytest.mark.parametrize(
    "flag,cmd",
    [
        ("--next", "next"),
        ("--prev", "prev"),
        ("--pause", "pause"),
        ("--resume", "resume"),
        ("--toggle", "toggle"),
        ("--status", "status"),
        ("--favourite", "favourite"),
        ("--hide", "hide"),
        ("--undo", "undo"),
    ],
)
def test_cli_payload_simple_flags(flag, cmd):
    assert ipc.cli_payload([flag]) == {"cmd": cmd}


def test_cli_payload_set_with_path():
    assert ipc.cli_payload(["--set", "D:\\photo.jpg"]) == {"cmd": "set", "path": "D:\\photo.jpg"}


def test_cli_payload_set_without_path_returns_none():
    assert ipc.cli_payload(["--set"]) is None


def test_cli_payload_first_recognised_flag_wins():
    # --set is checked first regardless of argv order.
    assert ipc.cli_payload(["--next", "--set", "x.jpg"]) == {"cmd": "set", "path": "x.jpg"}


# ---------------------------------------------------------------------------
# Mutex — live, Windows only (this dev/test machine is win32)
# ---------------------------------------------------------------------------

@WINDOWS_ONLY
def test_try_become_primary_second_caller_is_not_primary():
    handle1, primary1 = ipc.try_become_primary()
    try:
        assert primary1 is True
        handle2, primary2 = ipc.try_become_primary()
        try:
            assert primary2 is False
        finally:
            ipc.release_primary(handle2)
    finally:
        ipc.release_primary(handle1)


@WINDOWS_ONLY
def test_release_primary_lets_a_later_caller_become_primary():
    handle1, primary1 = ipc.try_become_primary()
    assert primary1 is True
    ipc.release_primary(handle1)
    handle2, primary2 = ipc.try_become_primary()
    try:
        assert primary2 is True
    finally:
        ipc.release_primary(handle2)


# ---------------------------------------------------------------------------
# Named-pipe server/client round trip — live, Windows only
# ---------------------------------------------------------------------------

@WINDOWS_ONLY
def test_ipc_server_round_trip():
    def dispatch(payload: dict) -> dict:
        return {"ok": True, "echo": payload}

    def marshal(fn) -> None:
        fn()  # no real Tk loop in this test — call synchronously

    server = ipc.IpcServer(dispatch, marshal)
    server.start()
    try:
        # Give the server a moment to open its first pipe instance.
        time.sleep(0.2)
        reply = ipc.send_command({"cmd": "status"}, timeout=3.0)
        assert reply == {"ok": True, "echo": {"cmd": "status"}}
    finally:
        server.stop()
        server.join(timeout=3.0)


@WINDOWS_ONLY
def test_ipc_server_invalid_json_gets_error_reply():
    server = ipc.IpcServer(lambda payload: {"ok": True}, lambda fn: fn())
    server.start()
    try:
        time.sleep(0.2)
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.CreateFileW(
            ipc.PIPE_NAME, ipc.GENERIC_READ | ipc.GENERIC_WRITE, 0, None, ipc.OPEN_EXISTING, 0, None
        )
        assert handle not in (0, -1)
        try:
            data = b"not json\n"
            written = wintypes.DWORD()
            kernel32.WriteFile(handle, data, len(data), ctypes.byref(written), None)
            buf = ctypes.create_string_buffer(ipc.BUFFER_SIZE)
            read = wintypes.DWORD()
            kernel32.ReadFile(handle, buf, ipc.BUFFER_SIZE, ctypes.byref(read), None)
            import json

            reply = json.loads(buf.raw[: read.value].decode("utf-8"))
            assert reply == {"ok": False, "error": "invalid request"}
        finally:
            kernel32.CloseHandle(handle)
    finally:
        server.stop()
        server.join(timeout=3.0)


@WINDOWS_ONLY
def test_send_command_with_no_server_raises_oserror():
    with pytest.raises(OSError):
        ipc.send_command({"cmd": "ping"}, timeout=0.5)
