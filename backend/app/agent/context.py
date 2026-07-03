"""Agent tool context: binds tools to a single user and stores intermediate
results. Both the Gemini orchestrator and the fallback use the same context —
this is the guarantee that "the agent actually consumes the model's output".
"""

from datetime import date, timedelta

from .. import db
from ..schemas import DailyPlan, HouseholdProfile
from ..tools import (forecast_consumption, forecast_production, get_tariff,
                     get_weather, optimize, read_memory, write_memory)


def _resolve_date(text: str | None) -> date:
    today = date.today()
    if not text or text in ("today", "bugun", "bugün"):
        return today
    if text in ("tomorrow", "yarin", "yarın"):
        return today + timedelta(days=1)
    try:
        return date.fromisoformat(text)
    except ValueError:
        return today + timedelta(days=1)


class ToolContext:
    """Lives for the duration of one request; logs every tool the agent calls."""

    def __init__(self, user_id: int, profile: HouseholdProfile):
        self.user_id = user_id
        self.profile = profile
        self.calls: list[str] = []
        self.last_plan: DailyPlan | None = None
        self._weather = {}
        self._production = {}
        self._consumption = {}
        self._tariff = {}

    # --- Tool surface exposed to the agent (names are the contract names) ---

    def get_weather(self, date: str | None = None) -> dict:
        d = _resolve_date(date)
        self.calls.append(f"get_weather({d})")
        self._weather[d] = get_weather(self.profile.lat, self.profile.lon, d)
        w = self._weather[d]
        return {"date": str(d), "total_irradiance_kwh_m2": round(sum(w.irradiance_wm2) / 1000, 2),
                "max_temp": max(w.temp_c), "avg_cloud": round(sum(w.cloud_pct) / 24, 1)}

    def forecast_production(self, date: str | None = None) -> dict:
        d = _resolve_date(date)
        self.calls.append(f"forecast_production({d})")
        if d not in self._weather:
            self._weather[d] = get_weather(self.profile.lat, self.profile.lon, d)
        self._production[d] = forecast_production(self._weather[d], self.profile.panel_kw)
        p = self._production[d]
        peak = max(range(24), key=lambda h: p.hourly_kwh[h])
        return {"date": str(d), "total_kwh": p.total_kwh,
                "peak_hour": peak, "peak_kwh": p.hourly_kwh[peak]}

    def forecast_consumption(self, date: str | None = None) -> dict:
        d = _resolve_date(date)
        self.calls.append(f"forecast_consumption({d})")
        self._consumption[d] = forecast_consumption(self.profile, d)
        return {"date": str(d), "total_kwh": self._consumption[d].total_kwh}

    def get_tariff(self, date: str | None = None) -> dict:
        d = _resolve_date(date)
        self.calls.append(f"get_tariff({d})")
        self._tariff[d] = get_tariff(d, self.profile.user_type,
                                     self.profile.tariff_type,
                                     monthly_kwh=self.profile.monthly_bill_kwh)
        tf = self._tariff[d]
        return {"tariff_type": self.profile.tariff_type,
                "cheapest_hour_tl": min(tf.hourly_price), "priciest_hour_tl": max(tf.hourly_price),
                "avg_sell_tl": tf.avg_sell_price,
                "note": "Hourly net-metering: sell price is ~30% below buy every hour, "
                        "so consuming production within that hour beats selling it."}

    def optimize(self, date: str | None = None, blocked_hours: list[int] | None = None) -> dict:
        d = _resolve_date(date)
        self.calls.append(f"optimize({d})")
        if d not in self._production:
            self.forecast_production(str(d))
        if d not in self._consumption:
            self.forecast_consumption(str(d))
        if d not in self._tariff:
            self.get_tariff(str(d))
        plan = optimize(self._production[d], self._consumption[d], self._tariff[d],
                        self.profile, set(blocked_hours or []))
        self.last_plan = plan
        db.save_plan(self.user_id, plan)
        return {
            "date": str(d),
            "items": [{"name": i.name, "type": i.type, "start": i.start_h,
                       "end": i.end_h, "saving_tl": [i.saving_tl_min, i.saving_tl_max],
                       "reason": i.reason_code} for i in plan.items],
            "total_saving_tl": [plan.total_saving_tl_min, plan.total_saving_tl_max],
            "co2_kg": plan.co2_saved_kg,
            "env": plan.chart_data.get("env", {}),
            "self_consumption_ratio": plan.self_consumption_ratio,
        }

    def read_memory(self) -> list[dict]:
        self.calls.append("read_memory")
        return read_memory(self.user_id)

    def write_memory(self, text: str) -> dict:
        self.calls.append(f"write_memory({text[:40]})")
        return write_memory(self.user_id, text, source="inferred")
