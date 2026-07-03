"""forecast_consumption tool — hourly base-load forecast (excl. flexible devices).

Method (reasoned in docs/METHOD.md):
1. Normalized hourly SHAPE: household profile template (UCI/London literature
   shape, shifted toward the Turkish evening peak) or a business working shape.
2. SCALE: user's bill kWh → daily kWh; seasonal correction.
3. Flexible devices' share is SUBTRACTED from base load — the optimizer places
   them.

Accuracy is ±20-30%; this uncertainty is reflected to the user as a TL range
(config.SAVING_UNCERTAINTY). The DS team improves the shape with LightGBM in
v1; the signature and schema are fixed.
"""

import math
from datetime import date

from ..schemas import ConsumptionForecast, HouseholdProfile

# Normalized hourly shapes (sum to 1.0) — source: household consumption
# literature shape, TR evening peak (19-22) emphasized.
_HOME_SHAPE = [
    0.028, 0.024, 0.022, 0.021, 0.022, 0.026,   # 00-05 night base
    0.034, 0.042, 0.044, 0.042, 0.040, 0.040,   # 06-11 morning
    0.042, 0.042, 0.041, 0.042, 0.046, 0.056,   # 12-17 afternoon
    0.068, 0.078, 0.080, 0.074, 0.058, 0.048,   # 18-23 evening peak
]

_BUSINESS_SHAPE = [
    0.012, 0.010, 0.010, 0.010, 0.010, 0.012,   # 00-05 (fridge etc. base)
    0.020, 0.040, 0.075, 0.085, 0.088, 0.088,   # 06-11
    0.085, 0.085, 0.088, 0.088, 0.082, 0.070,   # 12-17
    0.050, 0.035, 0.025, 0.016, 0.014, 0.012,   # 18-23
]


def _season_factor(day: date, user_type: str) -> float:
    """Summer AC / winter heating effect: simple ±15% sinusoidal correction."""
    day_no = day.timetuple().tm_yday
    summer = math.sin(math.pi * (day_no - 80) / 365)       # Jun-Aug ~1
    return 1.0 + (0.15 if user_type == "business" else 0.10) * abs(summer)


def forecast_consumption(profile: HouseholdProfile, day: date) -> ConsumptionForecast:
    shape = _HOME_SHAPE if profile.user_type == "home" else _BUSINESS_SHAPE

    # Subtract flexible devices' weekly energy from base load (~3 runs/week assumed)
    flexible_daily = sum(d.kwh * 3 / 7 for d in profile.devices)
    daily_kwh = max(profile.monthly_bill_kwh / 30.0 - flexible_daily, 1.0)
    daily_kwh *= _season_factor(day, profile.user_type)

    hourly = [round(daily_kwh * share, 3) for share in shape]
    return ConsumptionForecast(
        date=day,
        hourly_kwh=hourly,
        total_kwh=round(sum(hourly), 2),
        model_version="v0-profile",
    )
