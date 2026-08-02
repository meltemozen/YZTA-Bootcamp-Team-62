"""forecast_production tool — weather-aware hourly PV production forecast.

v1 uses a small bundled regression artifact whose inputs are exactly the data
the product has at runtime: Open-Meteo shortwave radiation, temperature, cloud
cover and the user's panel size. The training scripts in data/scripts can
rebuild the artifact from PVGIS hourly CSVs (see
data/scripts/compare_production_models.py for model selection and
data/scripts/train_production_model_lgbm.py for the deploy step).

The deployed path requires the bundled LightGBM artifact. Missing or invalid
artifacts are deployment errors; they must not silently change the calculation.
"""

import json
import os
from datetime import date
from functools import lru_cache

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
    except (OSError, json.JSONDecodeError) as err:
        raise RuntimeError("PV production model manifest is unavailable") from err


@lru_cache(maxsize=1)
def _load_lgbm_booster():
    """Load the exact production model declared by the manifest."""
    if not _HAS_LGBM:
        raise RuntimeError("lightgbm is required for production forecasting")
    model = _load_model()
    if model.get("model_type") != "lightgbm":
        raise RuntimeError("Unsupported PV production model type")
    model_file = os.path.join(_MODELS_DIR, model.get("model_file", "production_v1_lgbm.txt"))
    try:
        return lgb.Booster(model_file=model_file)
    except Exception as err:
        raise RuntimeError("PV production model artifact could not be loaded") from err


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


def forecast_production(weather: Weather, panel_kw: float) -> ProductionForecast:
    model = _load_model()
    booster = _load_lgbm_booster()

    try:
        hourly = _forecast_lgbm(booster, model, weather, panel_kw)
    except Exception as err:
        raise RuntimeError("PV production forecast failed") from err

    return ProductionForecast(
        date=weather.date,
        hourly_kwh=hourly,
        total_kwh=round(sum(hourly), 2),
        model_version=model["model_version"],
        trained_at=model.get("trained_at"),
        weather_source=weather.source,
    )


def forecast_production_for_day(lat: float, lon: float, day: date, panel_kw: float) -> ProductionForecast:
    """Convenience wrapper the agent can use in a single call."""
    from .weather import get_weather
    return forecast_production(get_weather(lat, lon, day), panel_kw)
