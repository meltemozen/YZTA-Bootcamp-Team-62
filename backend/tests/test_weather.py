"""Tests for tools/weather.py's live/cached/synthetic branching.

Weather.source is the contract the rest of the product relies on for
data-quality disclosure (agent system prompt, fallback templates,
WeatherCheck/ProductionForecast API fields, mobile UI notes) — a cached or
synthetic response silently mislabeled as "live" would defeat all of that.
Each test gets an isolated cache file so runs never leak into each other or
the developer's real weather cache.
"""

from datetime import date

import httpx
import pytest

from app.tools import production
from app.tools import weather as weather_module

LAT, LON = 38.42, 27.14
DAY = date(2026, 7, 30)


def _open_meteo_body():
    return {
        "hourly": {
            "shortwave_radiation": [0.0] * 24,
            "temperature_2m": [20.0] * 24,
            "cloud_cover": [10.0] * 24,
        },
        "current": {
            "shortwave_radiation": 100.0,
            "temperature_2m": 22.0,
            "cloud_cover": 5.0,
        },
    }


class _OkResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return _open_meteo_body()


def _network_down(*_args, **_kwargs):
    raise httpx.ConnectError("network down")


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(weather_module, "_CACHE", str(tmp_path / "cache.json"))


def test_live_call_marks_source_live(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _OkResponse())

    result = weather_module.get_weather(LAT, LON, DAY)

    assert result.source == "live"
    assert len(result.irradiance_wm2) == 24


def test_cache_hit_after_network_failure_marks_source_cached(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _OkResponse())
    weather_module.get_weather(LAT, LON, DAY)  # populates the cache

    monkeypatch.setattr(httpx, "get", _network_down)
    result = weather_module.get_weather(LAT, LON, DAY)

    assert result.source == "cached"


def test_network_failure_without_cache_marks_source_synthetic(monkeypatch):
    monkeypatch.setattr(httpx, "get", _network_down)

    result = weather_module.get_weather(LAT, LON, DAY)

    assert result.source == "synthetic"
    assert len(result.irradiance_wm2) == 24


def test_production_forecast_carries_weather_source(monkeypatch):
    """The disclosure has to survive forecast_production() too, since the
    Today-screen plan reads weather_source off ProductionForecast, not
    Weather directly."""
    monkeypatch.setattr(httpx, "get", _network_down)

    weather = weather_module.get_weather(LAT, LON, DAY)
    forecast = production.forecast_production(weather, panel_kw=5.0)

    assert forecast.weather_source == "synthetic"
