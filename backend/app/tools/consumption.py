"""forecast_consumption tool — hourly base-load forecast (excl. flexible devices).

v1 separates model SHAPE from user SCALE:
1. A bundled generic smart-meter shape artifact gives hourly home/business load.
2. The user's monthly bill calibrates the daily energy total.
3. Flexible devices are subtracted from base load; the optimizer places them.

This is intentionally generic: without a user's smart-meter history, a calibrated
public smart-meter shape is more honest than pretending to know the exact house.
"""

import json
import math
import os
from datetime import date
from functools import lru_cache

from ..schemas import ConsumptionForecast, HouseholdProfile

_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "models", "consumption_v1.json")


@lru_cache(maxsize=1)
def _load_model() -> dict:
    fallback_home = [
        0.028, 0.024, 0.022, 0.021, 0.022, 0.026,
        0.034, 0.042, 0.044, 0.042, 0.040, 0.040,
        0.042, 0.042, 0.041, 0.042, 0.046, 0.056,
        0.068, 0.078, 0.080, 0.074, 0.058, 0.048,
    ]
    fallback_business = [
        0.012, 0.010, 0.010, 0.010, 0.010, 0.012,
        0.020, 0.040, 0.075, 0.085, 0.088, 0.088,
        0.085, 0.085, 0.088, 0.088, 0.082, 0.070,
        0.050, 0.035, 0.025, 0.016, 0.014, 0.012,
    ]
    try:
        with open(_MODEL_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {
            "model_version": "v0-profile",
            "home_shape": fallback_home,
            "business_shape": fallback_business,
            "seasonality": {"home_amplitude": 0.10, "business_amplitude": 0.15},
            "weekend": {"home_multiplier": 1.0, "business_multiplier": 1.0},
        }


def _normalize(shape: list[float]) -> list[float]:
    total = sum(shape) or 1.0
    return [x / total for x in shape]


def _season_factor(day: date, user_type: str, model: dict) -> float:
    """Summer cooling / winter heating effect learned as a scalar modifier."""
    day_no = day.timetuple().tm_yday
    summer = math.sin(math.pi * (day_no - 80) / 365)       # Jun-Aug ~1
    key = "business_amplitude" if user_type == "business" else "home_amplitude"
    amplitude = model.get("seasonality", {}).get(key, 0.12)
    return 1.0 + amplitude * abs(summer)


def _weekend_factor(day: date, user_type: str, model: dict) -> float:
    if day.weekday() < 5:
        return 1.0
    key = "business_multiplier" if user_type == "business" else "home_multiplier"
    return float(model.get("weekend", {}).get(key, 1.0))


def forecast_consumption(profile: HouseholdProfile, day: date) -> ConsumptionForecast:
    model = _load_model()
    shape_key = "business_shape" if profile.user_type == "business" else "home_shape"
    shape = _normalize([float(x) for x in model[shape_key]])

    # Subtract flexible devices' weekly energy from base load (~3 runs/week assumed)
    flexible_daily = sum(d.kwh * 3 / 7 for d in profile.devices)
    daily_kwh = max(profile.monthly_bill_kwh / 30.0 - flexible_daily, 1.0)
    daily_kwh *= _season_factor(day, profile.user_type, model)
    daily_kwh *= _weekend_factor(day, profile.user_type, model)

    hourly = [round(daily_kwh * share, 3) for share in shape]
    return ConsumptionForecast(
        date=day,
        hourly_kwh=hourly,
        total_kwh=round(sum(hourly), 2),
        model_version=model.get("model_version", "v1-generic-load-shape"),
    )
