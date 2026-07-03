"""forecast_production tool — hourly PV production forecast.

v0: physical model (irradiance × capacity × performance ratio, temperature
corrected). Typical daily-total error ±10-15%; runs the product today.

FOR THE DS TEAM: when the LightGBM model is ready, replace the computation
inside `forecast_production`, do NOT touch the signature or the
ProductionForecast schema (set model_version to 'v1-lightgbm'). Use
data/scripts/pvgis_fetch.py for training data.
"""

from datetime import date

from .. import config
from ..schemas import ProductionForecast, Weather


def forecast_production(weather: Weather, panel_kw: float) -> ProductionForecast:
    hourly = []
    for irradiance, temp in zip(weather.irradiance_wm2, weather.temp_c):
        # Cell temp is higher than air temp; every degree above 25°C cuts power
        cell_temp = temp + config.PV_NOCT_FACTOR * irradiance
        temp_factor = 1 - config.PV_TEMP_COEFF * max(0.0, cell_temp - 25)
        kw = (irradiance / 1000.0) * panel_kw * config.PV_PERFORMANCE_RATIO * temp_factor
        hourly.append(round(min(max(kw, 0.0), panel_kw), 3))

    return ProductionForecast(
        date=weather.date,
        hourly_kwh=hourly,
        total_kwh=round(sum(hourly), 2),
        model_version="v0-physical",
    )


def forecast_production_for_day(lat: float, lon: float, day: date, panel_kw: float) -> ProductionForecast:
    """Convenience wrapper the agent can use in a single call."""
    from .weather import get_weather
    return forecast_production(get_weather(lat, lon, day), panel_kw)
