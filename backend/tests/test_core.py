"""Core logic tests: tariff, production, consumption, optimization.

No network — weather is built by hand and behaviour is deterministic.
Run: inside backend/ `python -m pytest tests/ -v`
"""

from datetime import date, timedelta

import pytest

from app import config
from app.schemas import Device, HouseholdProfile, Weather
from app.tools.consumption import forecast_consumption
from app.tools.optimize import optimize
from app.tools.production import forecast_production
from app.tools.tariff import get_tariff, time_band

# A fixed future offset, not a hardcoded calendar date: optimize() applies a
# "don't schedule in the past" runtime rule whenever the plan date equals
# date.today() (see optimize._runtime_blocked_hours), which blocks every hour
# before the current wall-clock hour. A hardcoded literal date (e.g.
# date(2026, 7, 15)) eventually collides with "today" as time passes and
# makes these deterministic-by-design tests fail depending on what time of
# day CI happens to run. Anchoring to date.today() + N days keeps the tests
# always describing a day in the future, so that runtime block never fires.
DAY = date.today() + timedelta(days=2)


def sunny_weather() -> Weather:
    """A typical summer day peaking at noon."""
    irradiance = [0.0] * 24
    for h in range(6, 20):
        irradiance[h] = 900 * max(0.0, 1 - abs(h - 13) / 7)
    return Weather(date=DAY, irradiance_wm2=irradiance,
                   temp_c=[28.0] * 24, cloud_pct=[10.0] * 24)


def cloudy_weather() -> Weather:
    sunny = sunny_weather()
    return Weather(date=DAY,
                   irradiance_wm2=[x * 0.25 for x in sunny.irradiance_wm2],
                   temp_c=[22.0] * 24,
                   cloud_pct=[90.0] * 24)


def make_profile(**changes) -> HouseholdProfile:
    base = dict(user_type="home", panel_kw=5.0, monthly_bill_kwh=300,
                tariff_type="single",
                devices=[Device(name="Çamaşır makinesi", kwh=1.0, duration_h=2,
                                earliest=8, latest=23)])
    base.update(changes)
    return HouseholdProfile(**base)


# --- Tariff ---

def test_time_bands_epdk_standard():
    assert time_band(6) == "day" and time_band(16) == "day"
    assert time_band(17) == "peak" and time_band(21) == "peak"
    assert time_band(22) == "night" and time_band(5) == "night"


def test_hourly_netmeter_sell_below_buy():
    """Hourly net-metering (Official Gazette 02.04.2026): sell is below buy every
    hour — the economic basis of the self-consumption priority."""
    for kind in ("single", "three_zone"):
        tariff = get_tariff(DAY, "home", kind, monthly_kwh=300)
        assert all(s < b for s, b in
                   zip(tariff.hourly_sell_price, tariff.hourly_price))


def test_residential_tier_marginal_price():
    """EPDK tiered tariff: consumers above 240 kWh/month see the high tier price."""
    low = get_tariff(DAY, "home", "single", monthly_kwh=200)
    high = get_tariff(DAY, "home", "single", monthly_kwh=350)
    assert high.hourly_price[0] > low.hourly_price[0]


def test_three_zone_peak_most_expensive():
    tariff = get_tariff(DAY, "home", "three_zone")
    assert tariff.hourly_price[19] > tariff.hourly_price[10] > tariff.hourly_price[3]


def test_external_price_vector_adapter(tmp_path, monkeypatch):
    price_file = tmp_path / "prices.json"
    price_file.write_text(
        '{"source":"test-dynamic","hourly_price":['
        + ",".join(["1"] * 12 + ["9"] * 12)
        + '],"hourly_sell_price":['
        + ",".join(["0.5"] * 24)
        + "]}",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "PRICE_VECTOR_FILE", str(price_file))

    tariff = get_tariff(DAY, "home", "single", monthly_kwh=300)

    assert tariff.source == "test-dynamic"
    assert tariff.hourly_price[0] == 1
    assert tariff.hourly_price[18] == 9
    assert tariff.hourly_sell_price[0] == 0.5


# --- Production ---

def test_production_zero_at_night_positive_by_day():
    production = forecast_production(sunny_weather(), panel_kw=5.0)
    assert production.hourly_kwh[2] == 0
    assert production.hourly_kwh[13] > 2.5          # noon peak
    assert max(production.hourly_kwh) <= 5.0        # capacity not exceeded
    assert production.total_kwh == pytest.approx(sum(production.hourly_kwh), abs=0.1)
    assert production.model_version.startswith("v1-")


def test_weather_aware_production_drops_on_cloudy_day():
    sunny = forecast_production(sunny_weather(), panel_kw=5.0)
    cloudy = forecast_production(cloudy_weather(), panel_kw=5.0)
    assert cloudy.total_kwh < sunny.total_kwh * 0.45


# --- Consumption ---

def test_consumption_calibrated_to_bill():
    profile = make_profile(devices=[])
    consumption = forecast_consumption(profile, DAY)
    # Daily ≈ bill/30, within the ±15% season factor
    assert 300 / 30 * 0.85 <= consumption.total_kwh <= 300 / 30 * 1.20
    # Home profile evening peak: 20:00 > 03:00
    assert consumption.hourly_kwh[20] > consumption.hourly_kwh[3] * 2
    assert consumption.model_version.startswith("v1-")


# --- Optimization: the heart of the product ---

def test_single_rate_device_lands_on_solar_hour():
    """Single-rate (most users): hourly net-metering sell loss (~×0.7) is always
    below buy → the device should land in the solar-surplus window (9-16)."""
    profile = make_profile()
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "single", monthly_kwh=300)

    plan = optimize(production, consumption, tariff, profile)
    device = next(i for i in plan.items if i.type == "device")
    assert 9 <= device.start_h <= 16
    assert device.reason_code in ("solar_surplus", "avoid_peak")
    assert plan.total_saving_tl_max > plan.total_saving_tl_min >= 0


def test_three_zone_device_never_enters_peak():
    """In three-zone the day SELL price can exceed the night BUY price → the
    device may shift to night (correct economics); but it must never enter the
    17-22 peak."""
    profile = make_profile(tariff_type="three_zone")
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "three_zone")

    plan = optimize(production, consumption, tariff, profile)
    device = next(i for i in plan.items if i.type == "device")
    run_hours = {(device.start_h + i) % 24 for i in range(2)}
    assert not any(17 <= h < 22 for h in run_hours)


def test_blocked_hours_are_respected():
    """A stored preference ('nobody home at noon') must actually change the plan."""
    profile = make_profile()
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "three_zone")

    blocked = set(range(9, 18))
    plan = optimize(production, consumption, tariff, profile, blocked_hours=blocked)
    device = next(i for i in plan.items if i.type == "device")
    run = {(device.start_h + i) % 24 for i in range(2)}
    assert not run & blocked


def test_today_plan_never_uses_past_hours():
    today = date.today()
    weather = sunny_weather().model_copy(update={"date": today})
    profile = make_profile(devices=[
        Device(name="Elektrikli araç şarjı", kwh=14.8, power_kw=7.4,
               duration_h=2, earliest=8, latest=23, category="ev_charger")
    ])
    production = forecast_production(weather, profile.panel_kw)
    consumption = forecast_consumption(profile, today)
    tariff = get_tariff(today, "home", "single", monthly_kwh=300)

    plan = optimize(production, consumption, tariff, profile, current_hour=15)
    device = next(i for i in plan.items if i.type == "device")

    assert device.start_h >= 15
    assert set(range(15)) <= set(plan.chart_data["optimization"]["blocked_hours"])


def test_multi_device_optimizer_reports_coordinate_descent_metadata():
    profile = make_profile(devices=[
        Device(name="Elektrikli araç şarjı", kwh=22.0, power_kw=7.4,
               duration_h=3, earliest=8, latest=23, category="ev_charger"),
        Device(name="Bulaşık makinesi", kwh=1.2, power_kw=0.6,
               duration_h=2, earliest=8, latest=23, category="appliance"),
        Device(name="Termosifon", kwh=2.0, power_kw=2.0,
               duration_h=1, earliest=8, latest=23, category="water_heating"),
    ])
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "single", monthly_kwh=450)

    plan = optimize(production, consumption, tariff, profile, blocked_hours={8, 9})

    ev = next(i for i in plan.items if i.name.startswith("Elektrikli araç"))
    ev_hours = {(ev.start_h + i) % 24 for i in range(3)}
    assert not ev_hours & {8, 9}
    assert plan.chart_data["optimization"]["device_optimizer"] == "greedy+coordinate_descent"
    assert plan.chart_data["optimization"]["cost_evaluations"] > 0


def test_battery_charges_by_day_discharges_at_peak():
    profile = make_profile(battery_kwh=5.0, battery_power_kw=2.5, monthly_bill_kwh=250)
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "three_zone")

    plan = optimize(production, consumption, tariff, profile)
    types = {i.type for i in plan.items}
    assert "battery_charge" in types and "battery_discharge" in types
    charge = next(i for i in plan.items if i.type == "battery_charge")
    assert 6 <= charge.start_h <= 17          # charge from solar


def test_self_consumption_ratio_sane():
    profile = make_profile()
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "three_zone")
    plan = optimize(production, consumption, tariff, profile)
    assert 0 <= plan.self_consumption_ratio <= 1
    assert plan.co2_saved_kg > 0
