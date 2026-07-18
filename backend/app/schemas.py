"""Model–Agent CONTRACT.

This file is the meeting point of the two teams (AI + Data Science) and is
LOCKED. Tool signatures and data types are defined here; changes require a
joint decision by both teams plus an update to docs/CONTRACT.md.

All hourly arrays have 24 elements and represent local time 00:00-23:00.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# User and household profile
# --------------------------------------------------------------------------

class Device(BaseModel):
    """Flexible load: a device whose run time the user can shift."""
    name: str
    kwh: float = Field(gt=0, description="Total consumption of one run (kWh)")
    duration_h: int = Field(ge=1, le=12, description="Run duration (hours, rounded up)")
    earliest: int = Field(default=0, ge=0, le=23)
    latest: int = Field(default=23, ge=0, le=23, description="Latest FINISH hour")


class HouseholdProfile(BaseModel):
    user_type: Literal["home", "business"] = "home"
    city: str = "İzmir"
    lat: float = 38.42
    lon: float = 27.14
    panel_kw: float = Field(gt=0, description="Installed panel power (kWp)")
    battery_kwh: float = Field(default=0, ge=0, description="Battery capacity, 0 = none")
    battery_power_kw: float = Field(default=0, ge=0, description="Max charge/discharge power")
    monthly_bill_kwh: float = Field(gt=0, description="Last bill monthly consumption — calibration input")
    tariff_type: Literal["single", "three_zone"] = "single"
    devices: list[Device] = []
    work_start: int = Field(default=8, ge=0, le=23, description="For businesses")
    work_end: int = Field(default=19, ge=0, le=23)


# --------------------------------------------------------------------------
# Tool inputs/outputs (the contract itself)
# --------------------------------------------------------------------------

class Weather(BaseModel):
    """Output of get_weather(location, date) — Open-Meteo live data."""
    date: date
    irradiance_wm2: list[float] = Field(description="Hourly global horizontal irradiance (W/m²), 24 elements")
    temp_c: list[float] = Field(description="Hourly temperature (°C), 24 elements")
    cloud_pct: list[float] = Field(description="Hourly cloud cover (%), 24 elements")


class ProductionForecast(BaseModel):
    """Output of forecast_production(weather, panel_kw)."""
    date: date
    hourly_kwh: list[float] = Field(description="24 elements")
    total_kwh: float
    model_version: str = Field(description="'v0-physical' | 'v1-lightgbm' — DS team swaps in v1")


class ConsumptionForecast(BaseModel):
    """Output of forecast_consumption(household_profile) — base load, EXCLUDING flexible devices."""
    date: date
    hourly_kwh: list[float]
    total_kwh: float
    model_version: str = "v0-profile"


class Tariff(BaseModel):
    """Output of get_tariff(date, user_type, tariff_type, monthly_kwh).

    Contract v1.1: hourly net-metering (Official Gazette 02.04.2026) required
    the sell price to be broken down per hour; the monthly_kwh input was added
    for tiered single-rate tariffs (marginal tier price selection).
    """
    date: date
    hourly_price: list[float] = Field(description="Buy price TL/kWh (incl. taxes), 24 elements")
    hourly_sell_price: list[float] = Field(
        description="Hourly net-metering sell price TL/kWh (≈ buy × 0.70), 24 elements")
    avg_sell_price: float = Field(description="Daily average sell price (back-compat/summary)")
    band: list[str] = Field(description="Per hour: 'day'|'peak'|'night'|'flat'")


class PlanItem(BaseModel):
    type: Literal["device", "battery_charge", "battery_discharge"]
    name: str
    start_h: int
    end_h: int
    saving_tl_min: float = Field(description="Uncertainty range lower bound")
    saving_tl_max: float
    reason_code: str = Field(description="'solar_surplus'|'avoid_peak'|'cheap_night'|'netmeter_edge'")


class DailyPlan(BaseModel):
    """Output of optimize(...) — the raw plan the agent turns into user text."""
    date: date
    items: list[PlanItem]
    total_saving_tl_min: float
    total_saving_tl_max: float
    co2_saved_kg: float
    self_consumption_ratio: float = Field(description="Share of production consumed at home 0-1")
    chart_data: dict = Field(default_factory=dict, description="For charts: production/consumption/price arrays")


class UserPreference(BaseModel):
    """read_memory/write_memory unit."""
    text: str = Field(description="e.g. 'Nobody is home on Tuesday afternoons'")
    source: Literal["user", "inferred"] = "user"
    date: str | None = None


# --------------------------------------------------------------------------
# API contracts (mobile ↔ backend)
# --------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    profile: HouseholdProfile


class RegisterResponse(BaseModel):
    user_id: int
    message: str


class AssistantRequest(BaseModel):
    user_id: int
    message: str = Field(description="Free Turkish: question, objection or preference")


class AssistantResponse(BaseModel):
    reply: str = Field(description="The agent's reasoned Turkish answer")
    plan: DailyPlan | None = None
    agent_mode: Literal["gemini", "fallback"]
    tool_calls: list[str] = Field(default_factory=list, description="Transparency: which tools were called")


class Feedback(BaseModel):
    user_id: int
    date: date
    item_name: str
    applied: bool


class MonthlyReport(BaseModel):
    month: str
    applied_count: int
    total_count: int
    realized_saving_tl_min: float
    realized_saving_tl_max: float
    missed_saving_tl: float = Field(description="Counterfactual: value of unapplied suggestions")
    co2_saved_kg: float
    # Environmental/social impact equivalents (SDG 7 & 13 narrative)
    car_km_equiv: float = Field(default=0, description="Car-km equivalent of avoided CO2")
    tree_month_equiv: float = Field(default=0, description="How many trees' monthly absorption")
    note: str
