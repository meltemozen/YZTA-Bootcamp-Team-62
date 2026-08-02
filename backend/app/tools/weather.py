"""Open-Meteo live weather and irradiance data.

Planning is deliberately strict: stale or generated weather must never be
presented as a current energy plan. If the provider is unavailable, callers
receive a service-unavailable error and can retry.
"""

import logging
from datetime import date
from zoneinfo import ZoneInfo

import httpx

from ..schemas import Weather

log = logging.getLogger(__name__)

_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherUnavailableError(RuntimeError):
    """Raised when a complete, current forecast cannot be obtained."""


def _current_hour() -> int:
    from datetime import datetime
    return datetime.now(ZoneInfo("Europe/Istanbul")).hour


def _apply_current_conditions(day: date, data: dict, current: dict | None) -> dict:
    if day != date.today() or not current:
        return data
    hour = _current_hour()
    mapping = {
        "shortwave_radiation": "irradiance",
        "temperature_2m": "temp",
        "cloud_cover": "cloud",
    }
    for current_key, data_key in mapping.items():
        value = current.get(current_key)
        if value is not None and len(data.get(data_key, [])) >= 24:
            data[data_key][hour] = value
    data["current_hour"] = hour
    data["current_irradiance"] = current.get("shortwave_radiation")
    data["current_temp"] = current.get("temperature_2m")
    data["current_cloud"] = current.get("cloud_cover")
    data["detail"] = "forecast+current"
    return data


def get_weather(lat: float, lon: float, day: date) -> Weather:
    try:
        resp = httpx.get(_URL, params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "shortwave_radiation,temperature_2m,cloud_cover",
            "current": "shortwave_radiation,temperature_2m,cloud_cover",
            "start_date": day.isoformat(),
            "end_date": day.isoformat(),
            "timezone": "Europe/Istanbul",
        }, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        hourly = body["hourly"]
        data = {
            "irradiance": hourly["shortwave_radiation"][:24],
            "temp": hourly["temperature_2m"][:24],
            "cloud": hourly["cloud_cover"][:24],
            "detail": "forecast",
        }
        if any(len(data[name]) != 24 or any(value is None for value in data[name])
               for name in ("irradiance", "temp", "cloud")):
            raise ValueError("Open-Meteo returned an incomplete hourly forecast")
        data = _apply_current_conditions(day, data, body.get("current"))
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as err:
        log.warning("Open-Meteo forecast unavailable: %s", err)
        raise WeatherUnavailableError("Güncel hava tahmini alınamadı") from err

    return Weather(
        date=day,
        irradiance_wm2=[float(x) for x in data["irradiance"]],
        temp_c=[float(x) for x in data["temp"]],
        cloud_pct=[float(x) for x in data["cloud"]],
        current_hour=data.get("current_hour"),
        current_irradiance_wm2=data.get("current_irradiance"),
        current_temp_c=data.get("current_temp"),
        current_cloud_pct=data.get("current_cloud"),
        source="live",
    )
