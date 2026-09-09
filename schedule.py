# Copyright (c) 2026 Mark Hawksworth (https://github.com/hawkers63/). All Rights Reserved.
#
# Desktop Vista is proprietary software. Unauthorised copying, reproduction,
# redistribution, modification, reverse-engineering, or commercial use of this
# file or any portion of it is strictly prohibited without prior written consent
# from the copyright holder (Mark Hawksworth — https://github.com/hawkers63/).
#
# See the LICENSE file in the project root for the full proprietary notice.
"""
Desktop Vista — solar/time-of-day scheduling (v1.6).

Pure, stdlib-only NOAA-style solar position arithmetic: sunrise/sunset and
civil-twilight crossing times for a given latitude/longitude and date, plus
the dawn/day/dusk/night phase this maps onto for biasing slideshow playback
(see notes/notes_005.txt §2.2.1). No Tk, no Windows API, no network — safe
to unit test without a display, and safe to call from the Tk thread since
every function here is a handful of trig calls.

Coordinates and dates are user/caller-supplied; this module never reads the
system clock, network, or geolocation itself.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

# Geometric centre of the sun at civil twilight (dawn/dusk boundary).
CIVIL_TWILIGHT_DEG = -6.0
# Standard refraction-corrected horizon crossing (sunrise/sunset boundary).
SUNRISE_SUNSET_DEG = -0.833

PHASES = ("dawn", "day", "dusk", "night")

# Tag aliases a user might apply to an image for a given phase — matched
# case-insensitively, without requiring the '#' prefix used in the UI.
PHASE_TAG_ALIASES: dict[str, set[str]] = {
    "dawn": {"dawn", "sunrise", "golden-hour-am"},
    "day": {"day", "daytime", "noon"},
    "dusk": {"dusk", "sunset", "golden-hour-pm"},
    "night": {"night", "dark"},
}


def _julian_day(dt: datetime) -> float:
    utc = dt.astimezone(timezone.utc)
    y, m = utc.year, utc.month
    d = utc.day + (utc.hour + utc.minute / 60 + utc.second / 3600) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = math.floor(y / 100)
    b = 2 - a + math.floor(a / 4)
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5


def _sun_times(
    lat: float, lon: float, day: datetime, altitude_deg: float
) -> Optional[tuple[datetime, datetime]]:
    """Return (morning, evening) local datetimes when the sun crosses
    *altitude_deg* on *day*'s local date. None if the sun never crosses
    that altitude that day (polar day/night at this latitude/season)."""
    jd = _julian_day(day.replace(hour=12, minute=0, second=0, microsecond=0))
    n = jd - 2451545.0 + 0.0008
    j_star = n - lon / 360.0
    m = (357.5291 + 0.98560028 * j_star) % 360
    m_rad = math.radians(m)
    c = 1.9148 * math.sin(m_rad) + 0.0200 * math.sin(2 * m_rad) + 0.0003 * math.sin(3 * m_rad)
    lam = (m + 102.9372 + c + 180) % 360
    j_transit = 2451545.0 + j_star + 0.0053 * math.sin(m_rad) - 0.0069 * math.sin(2 * math.radians(lam))
    sin_dec = math.sin(math.radians(lam)) * math.sin(math.radians(23.4397))
    dec = math.asin(sin_dec)
    lat_r = math.radians(lat)
    alt_r = math.radians(altitude_deg)
    denom = math.cos(lat_r) * math.cos(dec)
    if denom == 0:
        return None
    cos_ha = (math.sin(alt_r) - math.sin(lat_r) * math.sin(dec)) / denom
    if cos_ha < -1.0 or cos_ha > 1.0:
        return None
    ha = math.degrees(math.acos(cos_ha))
    j_rise = j_transit - ha / 360.0
    j_set = j_transit + ha / 360.0

    tz = day.tzinfo or datetime.now().astimezone().tzinfo

    def jd_to_local(j: float) -> datetime:
        unix = (j - 2440587.5) * 86400.0
        return datetime.fromtimestamp(unix, tz=timezone.utc).astimezone(tz)

    return jd_to_local(j_rise), jd_to_local(j_set)


def solar_phase_boundaries(lat: float, lon: float, now: datetime) -> dict[str, datetime]:
    """civil_dawn/sunrise/sunset/civil_dusk local datetimes for *now*'s
    date. A key is missing when the sun doesn't cross that altitude today
    (polar). *now* is used only for its local date and tzinfo."""
    local = now if now.tzinfo else now.astimezone()
    events: dict[str, datetime] = {}
    sunrise = _sun_times(lat, lon, local, SUNRISE_SUNSET_DEG)
    civil = _sun_times(lat, lon, local, CIVIL_TWILIGHT_DEG)
    if sunrise:
        events["sunrise"], events["sunset"] = sunrise
    if civil:
        events["civil_dawn"], events["civil_dusk"] = civil
    return events


def phase_from_fallback(now: datetime, fallback_times: list[str]) -> str:
    """Map *now* onto dawn/day/dusk/night using four HH:MM fallback times
    (dawn, day, dusk, night order), the same way daily-schedule mode reads
    clock times. Used when solar math can't run (no coordinates, or a
    polar location/date where the sun doesn't cross the relevant altitude)."""
    if len(fallback_times) != 4:
        return "day"
    hhmm: list[tuple[int, int]] = []
    for text in fallback_times:
        try:
            hour_str, minute_str = text.split(":")
            hhmm.append((int(hour_str), int(minute_str)))
        except (ValueError, AttributeError):
            return "day"
    phase = PHASES[-1]
    now_hm = (now.hour, now.minute)
    for name, hm in zip(PHASES, hhmm):
        if now_hm >= hm:
            phase = name
    return phase


def current_phase(
    lat: Optional[float], lon: Optional[float], now: datetime, fallback_times: list[str]
) -> str:
    """Which of dawn/day/dusk/night *now* falls in. Uses real sun-position
    math when both coordinates are given and the sun actually crosses the
    relevant altitudes on this date; otherwise degrades to the four
    fallback times so a polar location or an unset location never stalls."""
    if lat is not None and lon is not None:
        events = solar_phase_boundaries(lat, lon, now)
        if {"civil_dawn", "sunrise", "sunset", "civil_dusk"} <= events.keys():
            order = [
                ("dawn", events["civil_dawn"]),
                ("day", events["sunrise"]),
                ("dusk", events["sunset"]),
                ("night", events["civil_dusk"]),
            ]
            phase = "night"
            for name, when in order:
                if now >= when:
                    phase = name
            return phase
    return phase_from_fallback(now, fallback_times)


def next_boundary(lat: float, lon: float, now: datetime) -> Optional[datetime]:
    """Earliest future dawn/sunrise/sunset/dusk boundary strictly after
    *now*, or None if the sun doesn't cross the relevant altitudes on this
    date (caller should fall back to the fixed fallback times)."""
    events = solar_phase_boundaries(lat, lon, now)
    candidates = [v for v in events.values() if v > now]
    return min(candidates) if candidates else None


def phase_tag_matches(phase: str, tags: list[str]) -> bool:
    """True if any of *tags* is an alias for *phase* (case-insensitive)."""
    wanted = PHASE_TAG_ALIASES.get(phase, set())
    return bool(wanted & {t.lower() for t in tags})
