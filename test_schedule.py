# Copyright (c) 2026 hawkers63. All Rights Reserved.
"""Unit tests for schedule.py's solar/time-of-day math (no display / Tk required)."""

from __future__ import annotations

from datetime import datetime, timezone

import schedule as sch

LONDON = (51.5074, -0.1278)
SVALBARD = (78.0, 15.0)  # far enough north to see real polar day/night
FALLBACK = ["06:00", "08:00", "18:00", "21:00"]


# ---------------------------------------------------------------------------
# solar_phase_boundaries / next_boundary
# ---------------------------------------------------------------------------

def test_solar_phase_boundaries_are_correctly_ordered():
    now = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    events = sch.solar_phase_boundaries(*LONDON, now)
    assert events["civil_dawn"] < events["sunrise"] < events["sunset"] < events["civil_dusk"]


def test_solar_phase_boundaries_polar_summer_returns_empty():
    # Svalbard in June: the sun never sets — no altitude crossing at all.
    now = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    assert sch.solar_phase_boundaries(*SVALBARD, now) == {}


def test_solar_phase_boundaries_polar_winter_returns_empty():
    # Svalbard in December: the sun never rises.
    now = datetime(2026, 12, 21, 12, 0, tzinfo=timezone.utc)
    assert sch.solar_phase_boundaries(*SVALBARD, now) == {}


def test_next_boundary_returns_earliest_future_event():
    now = datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    events = sch.solar_phase_boundaries(*LONDON, now)
    boundary = sch.next_boundary(*LONDON, now)
    assert boundary == min(v for v in events.values() if v > now)
    assert boundary == events["sunset"]


def test_next_boundary_polar_returns_none():
    now = datetime(2026, 12, 21, 12, 0, tzinfo=timezone.utc)
    assert sch.next_boundary(*SVALBARD, now) is None


# ---------------------------------------------------------------------------
# current_phase
# ---------------------------------------------------------------------------

def test_current_phase_transitions_through_the_day():
    events = sch.solar_phase_boundaries(*LONDON, datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc))

    def phase_at(dt: datetime) -> str:
        return sch.current_phase(*LONDON, dt, FALLBACK)

    assert phase_at(events["civil_dawn"].replace(hour=0, minute=1)) == "night"
    assert phase_at(events["civil_dawn"]) == "dawn"
    assert phase_at(events["sunrise"]) == "day"
    assert phase_at(events["sunset"]) == "dusk"
    assert phase_at(events["civil_dusk"]) == "night"


def test_current_phase_polar_night_falls_back_to_fallback_times():
    now = datetime(2026, 12, 21, 19, 0, tzinfo=timezone.utc)  # no boundaries exist this date
    assert sch.current_phase(*SVALBARD, now, FALLBACK) == sch.phase_from_fallback(now, FALLBACK)


def test_current_phase_no_coordinates_uses_fallback_directly():
    now = datetime(2026, 6, 21, 19, 0, tzinfo=timezone.utc)
    assert sch.current_phase(None, None, now, FALLBACK) == sch.phase_from_fallback(now, FALLBACK)


# ---------------------------------------------------------------------------
# phase_from_fallback
# ---------------------------------------------------------------------------

def test_phase_from_fallback_ordering():
    cases = {
        (5, 0): "night",
        (6, 0): "dawn",
        (7, 59): "dawn",
        (8, 0): "day",
        (17, 59): "day",
        (18, 0): "dusk",
        (20, 59): "dusk",
        (21, 0): "night",
        (23, 59): "night",
    }
    for (hour, minute), expected in cases.items():
        now = datetime(2026, 1, 1, hour, minute)
        assert sch.phase_from_fallback(now, FALLBACK) == expected


def test_phase_from_fallback_invalid_times_defaults_to_day():
    assert sch.phase_from_fallback(datetime(2026, 1, 1, 3, 0), ["not-a-time"] * 4) == "day"
    assert sch.phase_from_fallback(datetime(2026, 1, 1, 3, 0), ["06:00"]) == "day"


# ---------------------------------------------------------------------------
# phase_tag_matches
# ---------------------------------------------------------------------------

def test_phase_tag_matches_aliases_case_insensitively():
    assert sch.phase_tag_matches("dusk", ["Sunset", "landscape"]) is True
    assert sch.phase_tag_matches("dusk", ["golden-hour-pm"]) is True
    assert sch.phase_tag_matches("night", ["dusk"]) is False
    assert sch.phase_tag_matches("day", []) is False


def test_phase_tag_matches_unknown_phase_never_matches():
    assert sch.phase_tag_matches("midnight-snack", ["night", "dark"]) is False
