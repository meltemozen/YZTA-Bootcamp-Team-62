"""Core logic tests: tariff, production, consumption, optimization.

No network — weather is built by hand and behaviour is deterministic.
Run: inside backend/ `python -m pytest tests/ -v`
"""

from datetime import date, timedelta

import pytest

from app import config
from app.schemas import CustomTariff, Device, HouseholdProfile, Weather
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
    # Home profile evening peak: 20:00 > 03:00 (ML calibrated shape is flatter but peak remains)
    assert consumption.hourly_kwh[20] > consumption.hourly_kwh[3]
    assert consumption.model_version.startswith("v")


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
    assert plan.chart_data["optimization"]["device_optimizer"] == "greedy+coordinate_descent+interruptible"
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


# --- S2-6: EV charging scenario (power feasibility + interruptible placement) ---

def _ev(name="Elektrikli araç şarjı", kwh=22.0, duration_h=3, **kw):
    defaults = dict(power_kw=7.4, earliest=8, latest=23,
                    category="ev_charger", flexibility="interruptible")
    defaults.update(kw)
    return Device(name=name, kwh=kwh, duration_h=duration_h, **defaults)


def test_ev_power_feasibility_extends_duration():
    """A 22 kWh top-up on a 7.4 kW charger physically needs 3 hours; a user
    typo of duration_h=1 must not compress it into one hour."""
    profile = make_profile(devices=[_ev(duration_h=1)])
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "single", monthly_kwh=450)

    plan = optimize(production, consumption, tariff, profile)
    ev_items = [i for i in plan.items if i.type == "device"]
    total_hours = sum((i.end_h - i.start_h) % 24 for i in ev_items)
    assert total_hours == 3  # ceil(22.0 / 7.4)


def test_ev_interruptible_splits_around_blocked_hour():
    """EV charging can pause: with an hour blocked in the middle of the solar
    window the charger routes around it instead of abandoning the window."""
    profile = make_profile(devices=[_ev()])
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "single", monthly_kwh=450)

    blocked = {12, 13}
    plan = optimize(production, consumption, tariff, profile, blocked_hours=blocked)
    ev_items = [i for i in plan.items if i.type == "device"]
    hours = set()
    for item in ev_items:
        hours |= set(range(item.start_h, item.start_h + (item.end_h - item.start_h) % 24))
    assert len(hours) == 3
    assert not hours & blocked
    # Still inside the productive part of the day (sunny profile peaks 9-16).
    assert hours <= set(range(9, 17)), hours
    # Split placements are labeled per segment for the mobile plan cards.
    if len(ev_items) > 1:
        assert all("bölüm" in i.name for i in ev_items)


def test_ev_interruptible_never_enters_peak_three_zone():
    profile = make_profile(tariff_type="three_zone", devices=[_ev()])
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "three_zone")

    plan = optimize(production, consumption, tariff, profile)
    for item in (i for i in plan.items if i.type == "device"):
        span = set(range(item.start_h, item.start_h + (item.end_h - item.start_h) % 24))
        assert not any(17 <= h < 22 for h in span)


def test_shiftable_appliance_stays_contiguous():
    """The interruptible path must not leak into ordinary appliances: a washing
    machine still runs as one uninterrupted block."""
    profile = make_profile()  # Çamaşır makinesi, flexibility unset
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "single", monthly_kwh=300)

    plan = optimize(production, consumption, tariff, profile,
                    blocked_hours={12})
    device_items = [i for i in plan.items if i.type == "device"]
    assert len(device_items) == 1
    assert "bölüm" not in device_items[0].name
    assert (device_items[0].end_h - device_items[0].start_h) % 24 == 2


def test_device_catalog_has_ev_and_interruptible_metadata():
    """Catalog acceptance for S2-6: ≥10 devices, EV entries physically
    consistent (kwh ≤ power_kw × schedulable hours) and marked interruptible."""
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "app", "data", "devices.json")
    with open(path, encoding="utf-8") as f:
        catalog = json.load(f)["devices"]
    assert len(catalog) >= 10
    evs = [d for d in catalog if d.get("category") == "ev_charger"]
    assert evs, "catalog must offer EV charging"
    for ev in evs:
        assert ev["flexibility"] == "interruptible"
        assert ev["kwh"] <= ev["power_kw"] * ev["duration_h"] + 1e-6 or \
            ev["kwh"] <= ev["power_kw"] * (ev["latest"] - ev["earliest"] + 1)
    # Every catalog row must satisfy the locked Device schema.
    for row in catalog:
        Device(**row)


# --- S3: user-defined tariff (the app's prices are a snapshot, not a feed) ---

def test_custom_single_price_overrides_regulated_table():
    regulated = get_tariff(DAY, "home", "single", monthly_kwh=300)
    custom = get_tariff(DAY, "home", "single", monthly_kwh=300,
                        custom=CustomTariff(single=4.10))
    assert custom.hourly_price == [4.10] * 24
    assert custom.hourly_price[0] != regulated.hourly_price[0]
    assert custom.source == "user-defined-single"
    # Sell price still derives from the user's own buy price.
    assert custom.hourly_sell_price[0] == round(4.10 * config.NETMETER_SELL_RATIO, 4)


def test_partial_custom_three_zone_keeps_regulated_for_blank_bands():
    """A user who only knows their peak price must not lose the other bands."""
    regulated = get_tariff(DAY, "home", "three_zone")
    custom = get_tariff(DAY, "home", "three_zone", custom=CustomTariff(peak=9.5))
    peak_hour = next(h for h in range(24) if custom.band[h] == "peak")
    day_hour = next(h for h in range(24) if custom.band[h] == "day")
    assert custom.hourly_price[peak_hour] == 9.5
    assert custom.hourly_price[day_hour] == regulated.hourly_price[day_hour]


def test_custom_sell_price_is_used_verbatim():
    tariff = get_tariff(DAY, "home", "single", monthly_kwh=300,
                        custom=CustomTariff(single=4.0, sell=3.10))
    assert tariff.hourly_sell_price == [3.10] * 24
    assert tariff.avg_sell_price == 3.10


def test_empty_custom_tariff_falls_back_to_regulated():
    regulated = get_tariff(DAY, "home", "single", monthly_kwh=300)
    empty = get_tariff(DAY, "home", "single", monthly_kwh=300, custom=CustomTariff())
    assert empty.hourly_price == regulated.hourly_price
    assert empty.source == regulated.source


def test_custom_tariff_changes_the_plan_economics():
    """The point of the feature: the user's own price drives the saving."""
    profile = make_profile(tariff_type="three_zone")
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)

    cheap = optimize(production, consumption,
                     get_tariff(DAY, "home", "three_zone", custom=CustomTariff(peak=6.0)),
                     profile)
    pricey = optimize(production, consumption,
                      get_tariff(DAY, "home", "three_zone", custom=CustomTariff(peak=15.0)),
                      profile)
    assert pricey.total_saving_tl_max > cheap.total_saving_tl_max


# --- S3: battery dispatch is reported as real windows, not min..max ---

def test_battery_windows_are_contiguous_and_do_not_overlap():
    """On a single-rate tariff every hour costs the same, so discharge hours
    scatter across the day. Reporting min..max as one block claimed a 24-hour
    discharge that overlapped the charge window — physically impossible."""
    profile = make_profile(battery_kwh=10.0, battery_power_kw=5.0, tariff_type="single")
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "single", monthly_kwh=profile.monthly_bill_kwh)

    plan = optimize(production, consumption, tariff, profile)
    charge_hours, discharge_hours = set(), set()
    for item in plan.items:
        span = range(item.start_h, item.end_h if item.end_h > item.start_h else item.end_h + 24)
        hours = {h % 24 for h in span}
        if item.type == "battery_charge":
            charge_hours |= hours
        elif item.type == "battery_discharge":
            discharge_hours |= hours

    assert charge_hours and discharge_hours
    assert not (charge_hours & discharge_hours), \
        "the battery cannot charge and discharge in the same hour"
    assert len(discharge_hours) < 24, "a 24-hour discharge window is not a real plan"


def test_battery_saving_is_split_across_reported_segments():
    profile = make_profile(battery_kwh=10.0, battery_power_kw=5.0, tariff_type="single")
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "single", monthly_kwh=profile.monthly_bill_kwh)

    plan = optimize(production, consumption, tariff, profile)
    discharge = [i for i in plan.items if i.type == "battery_discharge"]
    assert discharge
    if len(discharge) > 1:
        # Split items must be labelled so the UI can show them as one dispatch.
        assert all("bölüm" in i.name for i in discharge)
    assert all(i.saving_tl_min >= 0 for i in discharge)


# --- S3: multiple flexible devices competing for the same solar window ---

def test_multiple_devices_do_not_all_stack_on_one_hour():
    """Three shiftable loads + limited surplus: the optimizer must spread them
    rather than pile every device onto the single cheapest hour."""
    devices = [
        Device(name="Çamaşır makinesi", kwh=1.0, duration_h=2, earliest=0, latest=23),
        Device(name="Bulaşık makinesi", kwh=1.2, duration_h=2, earliest=0, latest=23),
        Device(name="Kurutma makinesi", kwh=2.5, duration_h=2, earliest=0, latest=23),
    ]
    profile = make_profile(devices=devices)
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "single", monthly_kwh=profile.monthly_bill_kwh)

    plan = optimize(production, consumption, tariff, profile)
    starts = [i.start_h for i in plan.items if i.type == "device"]
    assert len(starts) == 3
    assert len(set(starts)) > 1, "devices must not all start at the same hour"


def test_every_device_stays_inside_its_own_window():
    devices = [
        Device(name="Çamaşır makinesi", kwh=1.0, duration_h=2, earliest=9, latest=14),
        Device(name="Termosifon", kwh=3.0, duration_h=3, earliest=0, latest=6),
    ]
    profile = make_profile(devices=devices)
    production = forecast_production(sunny_weather(), profile.panel_kw)
    consumption = forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, "home", "three_zone")

    plan = optimize(production, consumption, tariff, profile)
    limits = {d.name: (d.earliest, d.latest) for d in devices}
    for item in plan.items:
        if item.type != "device":
            continue
        earliest, latest = limits[item.name.split(" (")[0]]
        assert item.start_h >= earliest
        end = item.end_h if item.end_h > item.start_h else item.end_h + 24
        assert end <= latest + 1
