"""forecast_production tool — weather-aware hourly PV production forecast.

v1 uses a small bundled regression artifact whose inputs are exactly the data
the product has at runtime: Open-Meteo shortwave radiation, temperature, cloud
cover and the user's panel size. The training script in data/scripts can rebuild
the artifact from PVGIS hourly CSVs; if the artifact is missing, the old physical
model still keeps the product working.
"""

import json
import math
import os
from datetime import date
from functools import lru_cache

from .. import config
from ..schemas import ProductionForecast, Weather

_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "models", "production_v1.json")


@lru_cache(maxsize=1)
def _load_model() -> dict:
    try:
        with open(_MODEL_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {
            "model_version": "v0-physical",
            "coefficients": {},
            "fallback_performance_ratio": config.PV_PERFORMANCE_RATIO,
            "blend_with_physical": 1.0,
            "max_kw_per_kwp": 1.0,
        }


def _physical_kw_per_kwp(irradiance: float, temp: float, performance_ratio: float) -> float:
    cell_temp = temp + config.PV_NOCT_FACTOR * irradiance
    temp_factor = 1 - config.PV_TEMP_COEFF * max(0.0, cell_temp - 25)
    return max(0.0, (irradiance / 1000.0) * performance_ratio * temp_factor)


def _solar_shape(day: date, hour: int) -> float:
    day_no = day.timetuple().tm_yday
    seasonal = max(0.0, math.sin(math.pi * (day_no - 80) / 365))
    daylight = 10.0 + 4.0 * seasonal
    sunrise = 12.0 - daylight / 2
    x = (hour - sunrise) / daylight
    return max(0.0, math.sin(math.pi * min(max(x, 0.0), 1.0)))


def forecast_production(weather: Weather, panel_kw: float) -> ProductionForecast:
    model = _load_model()
    coeff = model.get("coefficients", {})
    performance_ratio = float(model.get("fallback_performance_ratio", config.PV_PERFORMANCE_RATIO))
    blend = float(model.get("blend_with_physical", 0.25))
    max_per_kwp = float(model.get("max_kw_per_kwp", 1.0))

    hourly = []
    for hour, (irradiance, temp, cloud) in enumerate(
        zip(weather.irradiance_wm2, weather.temp_c, weather.cloud_pct)
    ):
        physical = _physical_kw_per_kwp(irradiance, temp, performance_ratio)
        shape = _solar_shape(weather.date, hour)
        edge_loss = max(0.0, 1.0 - shape)
        regressed = (
            float(model.get("intercept", 0.0))
            + coeff.get("ghi", 0.0) * irradiance
            + coeff.get("temp_loss", 0.0) * irradiance * max(temp - 25.0, 0.0)
            + coeff.get("cloud_interaction", 0.0) * irradiance * max(cloud, 0.0)
            + coeff.get("edge_hour_loss", 0.0) * edge_loss
        )
        kw_per_kwp = max(0.0, (1 - blend) * regressed + blend * physical)
        kw = min(kw_per_kwp, max_per_kwp) * panel_kw
        hourly.append(round(min(max(kw, 0.0), panel_kw), 3))

    return ProductionForecast(
        date=weather.date,
        hourly_kwh=hourly,
        total_kwh=round(sum(hourly), 2),
        model_version=model.get("model_version", "v1-weather-regressor"),
    )


def forecast_production_for_day(lat: float, lon: float, day: date, panel_kw: float) -> ProductionForecast:
    """Convenience wrapper the agent can use in a single call."""
    from .weather import get_weather
    return forecast_production(get_weather(lat, lon, day), panel_kw)
