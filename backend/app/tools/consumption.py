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
from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from ..schemas import ConsumptionForecast, HouseholdProfile
from .device_state import running_remaining_hours

_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "models", "consumption_v1.json")


@lru_cache(maxsize=1)
def _load_model() -> dict:
    try:
        with open(_MODEL_PATH, encoding="utf-8") as f:
            model = json.load(f)
    except (OSError, json.JSONDecodeError) as err:
        raise RuntimeError("Consumption model artifact is unavailable") from err
    if any(len(model.get(key, [])) != 24 for key in ("home_shape", "business_shape")):
        raise RuntimeError("Consumption model artifact is invalid")
    return model


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

    # Only separately-scheduled devices are subtracted from the calibrated base.
    flexible_devices = [
        device for device in profile.devices
        if device.enabled and (device.flexibility or "shiftable").lower() != "fixed"
    ]
    flexible_daily = sum(device.kwh * 3 / 7 for device in flexible_devices)
    daily_kwh = max(profile.monthly_bill_kwh / 30.0 - flexible_daily, 1.0)
    daily_kwh *= _season_factor(day, profile.user_type, model)
    daily_kwh *= _weekend_factor(day, profile.user_type, model)

    hourly = [daily_kwh * share for share in shape]

    # A device marked as running is an observed load for today, not another
    # optimization candidate. Add its remaining cycle to the current curve.
    now = datetime.now(ZoneInfo("Europe/Istanbul"))
    for device in flexible_devices:
        remaining = running_remaining_hours(device, day, now)
        if remaining <= 0:
            continue
        per_hour = device.kwh / max(device.duration_h, 1)
        for hour in range(now.hour, min(now.hour + remaining, 24)):
            hourly[hour] += per_hour

    hourly = [round(value, 3) for value in hourly]
    return ConsumptionForecast(
        date=day,
        hourly_kwh=hourly,
        total_kwh=round(sum(hourly), 2),
        model_version=model["model_version"],
        trained_at=model["trained_at"],
    )
