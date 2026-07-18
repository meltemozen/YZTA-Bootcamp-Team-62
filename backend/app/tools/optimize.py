"""optimize tool — device + battery daily plan.

Decision logic (deterministic and explainable — the jury question "why 13:00?"
is answered here):

* Net load per hour = base consumption − production.
* Imported kWh is valued at the buy price, exported kWh at the NET-METERING
  sell price. Since sell < buy, consuming production at home (self-consumption)
  is always more profitable than exporting — this is where Turkey's
  net-metering regulation shows up in the plan.
* Devices are placed largest-first, at the start hour that minimizes total cost
  within their allowed window (exhaustive 24-hour scan).
* Saving is computed against a "habit hour" reference (home: 19:00 evening peak,
  business: work start) and reported as a RANGE due to consumption uncertainty.
* Battery: charge during production-surplus hours, discharge during the most
  expensive import hours (90% round-trip efficiency).
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from .. import config
from ..schemas import (
    ConsumptionForecast,
    DailyPlan,
    Device,
    HouseholdProfile,
    PlanItem,
    ProductionForecast,
    Tariff,
)


def _profile_cost(net: list[float], price: list[float], sell: list[float]) -> float:
    """Daily TL cost — HOURLY net-metering (Official Gazette 02.04.2026):
    each hour nets separately; imports valued at that hour's buy price, exports
    at that hour's sell price."""
    total = 0.0
    for hour in range(24):
        if net[hour] > 0:
            total += net[hour] * price[hour]
        else:
            total -= (-net[hour]) * sell[hour]
    return total


def _add_device(net: list[float], device: Device, start: int) -> list[float]:
    new = net[:]
    per_hour = device.kwh / device.duration_h
    for i in range(device.duration_h):
        new[(start + i) % 24] += per_hour
    return new


def _remove_device(net: list[float], device: Device, start: int) -> list[float]:
    new = net[:]
    per_hour = device.kwh / device.duration_h
    for i in range(device.duration_h):
        new[(start + i) % 24] -= per_hour
    return new


def _valid_starts(device: Device, blocked: set[int]) -> list[int]:
    candidates = []
    for s in range(24):
        end = s + device.duration_h - 1
        if s < device.earliest or end > device.latest:
            continue
        if any((s + i) % 24 in blocked for i in range(device.duration_h)):
            continue
        candidates.append(s)
    return candidates


def _current_hour() -> int:
    return datetime.now(ZoneInfo("Europe/Istanbul")).hour


def _runtime_blocked_hours(plan_date: date, current_hour: int | None) -> set[int]:
    if plan_date != date.today():
        return set()
    hour = _current_hour() if current_hour is None else current_hour
    return set(range(max(0, min(hour, 23))))


def _reason(start: int, production: list[float], consumption: list[float],
            bands: list[str]) -> str:
    if production[start] > consumption[start]:
        return "solar_surplus"
    if bands[start] == "night":
        return "cheap_night"
    if bands[(start + 23) % 24] == "peak" or bands[start] != "peak":
        return "avoid_peak"
    return "netmeter_edge"


def optimize(production: ProductionForecast, consumption: ConsumptionForecast,
             tariff: Tariff, profile: HouseholdProfile,
             blocked_hours: set[int] | None = None,
             current_hour: int | None = None) -> DailyPlan:
    blocked = (blocked_hours or set()) | _runtime_blocked_hours(production.date, current_hour)
    price, sell = tariff.hourly_price, tariff.hourly_sell_price
    net = [c - p for c, p in zip(consumption.hourly_kwh, production.hourly_kwh)]

    items: list[PlanItem] = []
    reference_hour = 19 if profile.user_type == "home" else profile.work_start
    scheduled: list[tuple[Device, int]] = []
    cost_evaluations = 0

    # --- Device placement (largest load first) ---
    for device in sorted(profile.devices, key=lambda d: d.kwh, reverse=True):
        candidates = _valid_starts(device, blocked)
        if not candidates:
            continue
        costs = {s: _profile_cost(_add_device(net, device, s), price, sell)
                 for s in candidates}
        cost_evaluations += len(costs)
        # On a cost tie, pick the window with the most production surplus: the
        # safest hour against forecast error (the midday peak).
        def _surplus(s: int) -> float:
            return sum(max(-net[(s + i) % 24], 0.0) for i in range(device.duration_h))
        best = min(costs, key=lambda s: (round(costs[s], 2), -_surplus(s)))
        scheduled.append((device, best))
        net = _add_device(net, device, best)

    # Greedy is fast but can be locally suboptimal when multiple large loads
    # compete for the same solar window. Coordinate descent rechecks each device
    # against the placement of the others; 24h horizon keeps this cheap.
    for _ in range(3):
        changed = False
        for idx, (device, current_start) in enumerate(scheduled):
            candidates = _valid_starts(device, blocked)
            if not candidates:
                continue
            net_without = _remove_device(net, device, current_start)
            costs = {s: _profile_cost(_add_device(net_without, device, s), price, sell)
                     for s in candidates}
            cost_evaluations += len(costs)
            best = min(costs, key=lambda s: (round(costs[s], 2), -sum(
                max(-net_without[(s + i) % 24], 0.0) for i in range(device.duration_h)
            )))
            if round(costs[best], 4) < round(costs[current_start], 4):
                scheduled[idx] = (device, best)
                net = _add_device(net_without, device, best)
                changed = True
        if not changed:
            break

    for device, best in scheduled:
        net_without = _remove_device(net, device, best)
        candidates = _valid_starts(device, blocked)
        if not candidates:
            continue
        ref = reference_hour if reference_hour in candidates else max(
            candidates,
            key=lambda s: _profile_cost(_add_device(net_without, device, s), price, sell),
        )
        best_cost = _profile_cost(_add_device(net_without, device, best), price, sell)
        ref_cost = _profile_cost(_add_device(net_without, device, ref), price, sell)
        cost_evaluations += 2
        saving = max(ref_cost - best_cost, 0.0)
        u = config.SAVING_UNCERTAINTY

        items.append(PlanItem(
            type="device", name=device.name,
            start_h=best,
            end_h=(best + device.duration_h) % 24,
            saving_tl_min=round(saving * (1 - u), 2),
            saving_tl_max=round(saving * (1 + u), 2),
            reason_code=_reason(best, production.hourly_kwh, consumption.hourly_kwh,
                                tariff.band),
        ))

    # --- Battery: charge with surplus production, discharge at expensive hours ---
    if profile.battery_kwh > 0 and profile.battery_power_kw > 0:
        efficiency = 0.90
        allowed_hours = set(range(24)) - blocked
        charge_hours = sorted((h for h in allowed_hours if net[h] < 0),
                              key=lambda h: net[h])  # most surplus first
        stored, charge_window = 0.0, []
        for h in charge_hours:
            if stored >= profile.battery_kwh * 0.95:
                break
            taken = min(-net[h], profile.battery_power_kw,
                        profile.battery_kwh * 0.95 - stored)
            if taken <= 0.05:
                continue
            net[h] += taken
            stored += taken
            charge_window.append(h)

        discharge_hours = sorted((h for h in allowed_hours if net[h] > 0),
                                 key=lambda h: price[h], reverse=True)
        gain, discharge_window = 0.0, []
        available = stored * efficiency
        avg_sell = sum(sell) / 24
        for h in discharge_hours:
            if available <= 0.05:
                break
            given = min(net[h], profile.battery_power_kw, available)
            net[h] -= given
            available -= given
            # Gain: avoided grid import − revenue if it had been sold via netting
            gain += given * price[h] - (given / efficiency) * avg_sell
            discharge_window.append(h)

        if charge_window and discharge_window:
            u = config.SAVING_UNCERTAINTY
            items.append(PlanItem(
                type="battery_charge", name="Battery",
                start_h=min(charge_window), end_h=max(charge_window) + 1,
                saving_tl_min=0, saving_tl_max=0, reason_code="solar_surplus"))
            items.append(PlanItem(
                type="battery_discharge", name="Battery",
                start_h=min(discharge_window), end_h=max(discharge_window) + 1,
                saving_tl_min=round(max(gain, 0) * (1 - u), 2),
                saving_tl_max=round(max(gain, 0) * (1 + u), 2),
                reason_code="avoid_peak"))

    # --- Summary metrics ---
    self_consumed = sum(min(p, p + n) if n < 0 else p
                        for p, n in zip(production.hourly_kwh, net))
    self_ratio = round(min(self_consumed / production.total_kwh, 1.0), 2) if production.total_kwh > 0 else 0.0
    co2 = round(self_consumed * config.CO2_KG_PER_KWH, 2)

    return DailyPlan(
        date=production.date,
        items=items,
        total_saving_tl_min=round(sum(i.saving_tl_min for i in items), 2),
        total_saving_tl_max=round(sum(i.saving_tl_max for i in items), 2),
        co2_saved_kg=co2,
        self_consumption_ratio=self_ratio,
        chart_data={
            "production": production.hourly_kwh,
            "consumption": consumption.hourly_kwh,
            "price": tariff.hourly_price,
            "band": tariff.band,
            "models": {
                "production": production.model_version,
                "consumption": consumption.model_version,
            },
            "optimization": {
                "blocked_hours": sorted(blocked),
                "current_hour": current_hour if current_hour is not None
                else (_current_hour() if production.date == date.today() else None),
                "price_adapter": tariff.source,
                "device_optimizer": "greedy+coordinate_descent",
                "cost_evaluations": cost_evaluations,
            },
            # Environmental equivalents: make CO2 tangible (Ministry EF + widely
            # accepted equivalents, sources in config.py)
            "env": {
                "car_km": round(co2 / config.CAR_KG_CO2_KM, 1),
                "tree_days": round(co2 / (config.TREE_KG_CO2_YEAR / 365), 1),
            },
        },
    )
