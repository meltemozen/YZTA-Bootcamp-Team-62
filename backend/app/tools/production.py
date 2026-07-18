"""forecast_production tool — weather-aware hourly PV production forecast.

v1 uses a small bundled regression artifact whose inputs are exactly the data
the product has at runtime: Open-Meteo shortwave radiation, temperature, cloud
cover and the user's panel size. The training scripts in data/scripts can
rebuild the artifact from PVGIS hourly CSVs (see
data/scripts/compare_production_models.py for model selection and
data/scripts/train_production_model_lgbm.py for the deploy step).

Two artifact shapes are supported, both described by backend/app/models/production_v1.json:
  - model_type == "lightgbm": a LightGBM booster (production_v1_lgbm.txt,
    LightGBM's own text format — no pickle/joblib version lock-in). Requires
    the optional `lightgbm` package (backend/requirements.txt).
  - anything else (or lightgbm not installed / file missing): the original
    hand-rolled linear regressor blended with the physical model — pure
    Python, zero extra dependencies. This is also the safety net: if the
    LightGBM artifact or library is unavailable for any reason, the product
    keeps working instead of erroring out.
"""

import json
import math
import os
from datetime import date
from functools import lru_cache

from .. import config
from ..schemas import ProductionForecast, Weather

try:
    import lightgbm as lgb
    _HAS_LGBM = True
except ImportError:
    _HAS_LGBM = False

_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
_MODEL_PATH = os.path.join(_MODELS_DIR, "production_v1.json")

# Must match the feature engineering in data/scripts/compare_production_models.py
# and data/scripts/train_production_model_lgbm.py exactly, or predictions will
# be silently wrong.
_LGBM_FEATURE_ORDER = ["irradiance_wm2", "temp_loss_interaction", "cloud_interaction", "edge_hour_loss"]


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


@lru_cache(maxsize=1)
def _load_lgbm_booster():
    """Returns a lightgbm.Booster, or None if unavailable for any reason.

    Never raises — a missing/broken LightGBM artifact must fall back to the
    physical model, not take the product down.
    """
    if not _HAS_LGBM:
        return None
    model = _load_model()
    if model.get("model_type") != "lightgbm":
        return None
    model_file = os.path.join(_MODELS_DIR, model.get("model_file", "production_v1_lgbm.txt"))
    try:
        return lgb.Booster(model_file=model_file)
    except Exception:
        return None


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


def _forecast_lgbm(booster, model: dict, weather: Weather, panel_kw: float) -> list[float]:
    max_per_kwp = float(model.get("max_kw_per_kwp", 1.0))
    rows = []
    for hour, (irradiance, temp, cloud) in enumerate(
        zip(weather.irradiance_wm2, weather.temp_c, weather.cloud_pct)
    ):
        edge_hour_loss = abs(hour - 12) / 12.0
        rows.append([
            irradiance,
            irradiance * max(temp - 25.0, 0.0),
            irradiance * max(cloud, 0.0),
            edge_hour_loss,
        ])
    preds = booster.predict(rows)

    hourly = []
    for irradiance, pred in zip(weather.irradiance_wm2, preds):
        kw_per_kwp = 0.0 if irradiance <= 0 else max(0.0, float(pred))
        kw = min(kw_per_kwp, max_per_kwp) * panel_kw
        hourly.append(round(min(max(kw, 0.0), panel_kw), 3))
    return hourly


def _forecast_linear_physical(model: dict, weather: Weather, panel_kw: float) -> list[float]:
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
    return hourly


def forecast_production(weather: Weather, panel_kw: float) -> ProductionForecast:
    model = _load_model()
    booster = _load_lgbm_booster()

    if booster is not None:
        try:
            hourly = _forecast_lgbm(booster, model, weather, panel_kw)
            model_version = model.get("model_version", "v1-lightgbm")
        except Exception:
            # Any runtime failure in the ML path falls back to the linear/physical
            # blend rather than breaking the product.
            hourly = _forecast_linear_physical(model, weather, panel_kw)
            model_version = "v1-weather-regressor (lgbm fallback)"
    else:
        hourly = _forecast_linear_physical(model, weather, panel_kw)
        model_version = model.get("model_version", "v1-weather-regressor")

    return ProductionForecast(
        date=weather.date,
        hourly_kwh=hourly,
        total_kwh=round(sum(hourly), 2),
        model_version=model_version,
    )


def forecast_production_for_day(lat: float, lon: float, day: date, panel_kw: float) -> ProductionForecast:
    """Convenience wrapper the agent can use in a single call."""
    from .weather import get_weather
    return forecast_production(get_weather(lat, lon, day), panel_kw)
