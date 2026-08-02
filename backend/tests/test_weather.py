"""Strict live-weather contract tests."""

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


class _Response:
    def __init__(self, body=None):
        self.body = body or _open_meteo_body()

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


def test_live_call_returns_complete_forecast(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Response())
    result = weather_module.get_weather(LAT, LON, DAY)
    assert result.source == "live"
    assert len(result.irradiance_wm2) == 24


def test_network_failure_does_not_generate_weather(monkeypatch):
    def network_down(*_args, **_kwargs):
        raise httpx.ConnectError("network down")

    monkeypatch.setattr(httpx, "get", network_down)
    with pytest.raises(weather_module.WeatherUnavailableError):
        weather_module.get_weather(LAT, LON, DAY)


def test_incomplete_provider_response_is_rejected(monkeypatch):
    body = _open_meteo_body()
    body["hourly"]["cloud_cover"] = [10.0] * 23
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Response(body))
    with pytest.raises(weather_module.WeatherUnavailableError):
        weather_module.get_weather(LAT, LON, DAY)


def test_production_forecast_carries_live_source(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Response())
    weather = weather_module.get_weather(LAT, LON, DAY)
    forecast = production.forecast_production(weather, panel_kw=5.0)
    assert forecast.weather_source == "live"
