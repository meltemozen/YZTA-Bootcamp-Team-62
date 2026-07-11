"""get_weather tool — Open-Meteo live weather/irradiance data.

Requires no API key. Serves both as the agent's live tool and (via the
historical endpoint) as the DS team's model training data source.
On network error the last successful response is returned from cache; if that
is missing too, a seasonal synthetic profile is generated so the product never
shows an empty screen.
"""

import json
import logging
import math
import os
import tempfile
from datetime import date

import httpx

from ..schemas import Weather

log = logging.getLogger(__name__)

_CACHE = os.path.join(tempfile.gettempdir(), "wattra_weather_cache.json")
_URL = "https://api.open-meteo.com/v1/forecast"


def _write_cache(key: str, data: dict) -> None:
    try:
        current = {}
        if os.path.exists(_CACHE):
            try:
                with open(_CACHE, encoding="utf-8") as f:
                    current = json.load(f)
            except json.JSONDecodeError:
                current = {}  # corrupt cache (e.g. interrupted write) — start fresh
        current[key] = data
        with open(_CACHE, "w", encoding="utf-8") as f:
            json.dump(current, f)
    except OSError:
        pass


def _read_cache(key: str) -> dict | None:
    try:
        with open(_CACHE, encoding="utf-8") as f:
            return json.load(f).get(key)
    except (OSError, json.JSONDecodeError):
        return None


def _synthetic(day: date) -> dict:
    """No network at all: a rough clear-sky profile by season."""
    day_no = day.timetuple().tm_yday
    season = math.sin(math.pi * (day_no - 80) / 365)  # midsummer ~1
    peak = 550 + 400 * max(season, 0)
    irradiance = [max(0.0, peak * math.sin(math.pi * (h - 5.5) / 13)) if 6 <= h <= 19 else 0.0
                  for h in range(24)]
    temp = [12 + 12 * max(season, 0) + 6 * math.sin(math.pi * (h - 9) / 12) for h in range(24)]
    return {"irradiance": irradiance, "temp": temp, "cloud": [20.0] * 24}


def get_weather(lat: float, lon: float, day: date) -> Weather:
    key = f"{lat:.2f},{lon:.2f},{day.isoformat()}"
    try:
        resp = httpx.get(_URL, params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "shortwave_radiation,temperature_2m,cloud_cover",
            "start_date": day.isoformat(),
            "end_date": day.isoformat(),
            "timezone": "Europe/Istanbul",
        }, timeout=15)
        resp.raise_for_status()
        hourly = resp.json()["hourly"]
        data = {
            "irradiance": hourly["shortwave_radiation"][:24],
            "temp": hourly["temperature_2m"][:24],
            "cloud": hourly["cloud_cover"][:24],
        }
        _write_cache(key, data)
    except (httpx.HTTPError, KeyError) as err:
        log.warning("Open-Meteo unreachable (%s), using cache/synthetic", err)
        data = _read_cache(key) or _synthetic(day)

    return Weather(
        date=day,
        irradiance_wm2=[float(x or 0) for x in data["irradiance"]],
        temp_c=[float(x or 15) for x in data["temp"]],
        cloud_pct=[float(x or 0) for x in data["cloud"]],
    )
