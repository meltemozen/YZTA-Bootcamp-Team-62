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
* S2-6 EV realism: `power_kw` bounds the physics — a run cannot finish faster
  than kwh/power_kw hours (effective duration). Devices marked
  `flexibility="interruptible"` (EV chargers, pumps) may PAUSE: their hours are
  chosen greedily by marginal cost and need not be contiguous, so an EV routes
  around blocked hours and hugs the solar window. Multi-segment placements are
  reported as one PlanItem per contiguous segment.
* Saving is computed against a "habit hour" reference (home: 19:00 evening peak,
  business: work start) and reported as a RANGE due to consumption uncertainty.
* Battery: charge during production-surplus hours, discharge during the most
  expensive import hours (90% round-trip efficiency).
"""

import math
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


def _effective_duration(device: Device) -> int:
    """Physical feasibility (S2-6): a run cannot finish faster than
    kwh / power_kw hours. A 22 kWh EV top-up on a 7.4 kW charger needs 3 h even
    if the user typed duration_h=1."""
    if device.power_kw:
        return min(24, max(device.duration_h, math.ceil(device.kwh / device.power_kw - 1e-9)))
    return device.duration_h


def _is_interruptible(device: Device) -> bool:
    return (device.flexibility or "").lower() == "interruptible"


def _add_hours(net: list[float], device: Device, hours: tuple[int, ...]) -> list[float]:
    new = net[:]
    per_hour = device.kwh / len(hours)
    for h in hours:
        new[h % 24] += per_hour
    return new


def _remove_hours(net: list[float], device: Device, hours: tuple[int, ...]) -> list[float]:
    new = net[:]
    per_hour = device.kwh / len(hours)
    for h in hours:
        new[h % 24] -= per_hour
    return new


def _valid_starts(device: Device, blocked: set[int], duration: int) -> list[int]:
    candidates = []
    for s in range(24):
        end = s + duration - 1
        if s < device.earliest or end > device.latest:
            continue
        if any((s + i) % 24 in blocked for i in range(duration)):
            continue
        candidates.append(s)
    return candidates


def _contiguous_placements(device: Device, blocked: set[int],
                           duration: int) -> list[tuple[int, ...]]:
    return [tuple(range(s, s + duration))
            for s in _valid_starts(device, blocked, duration)]


def _greedy_interruptible_hours(net: list[float], device: Device, blocked: set[int],
                                duration: int, price: list[float],
                                sell: list[float]) -> tuple[int, ...] | None:
    """Cheapest `duration` hours in the window, chosen one by one by marginal
    cost (deterministic and explainable: 'the cheapest hours, solar first').
    Hours need not be contiguous — this is how an EV pauses and resumes."""
    window = [h for h in range(device.earliest, device.latest + 1) if h not in blocked]
    if len(window) < duration:
        return None
    per_hour = device.kwh / duration
    chosen: list[int] = []
    working = net[:]
    for _ in range(duration):
        def _marginal(h: int) -> float:
            added_import = max(working[h] + per_hour, 0.0) - max(working[h], 0.0)
            lost_export = max(-working[h], 0.0) - max(-(working[h] + per_hour), 0.0)
            return added_import * price[h] + lost_export * sell[h]
        # Tie-break on the hour itself keeps the choice deterministic.
        best = min((h for h in window if h not in chosen),
                   key=lambda h: (round(_marginal(h), 6), h))
        chosen.append(best)
        working[best] += per_hour
    return tuple(sorted(chosen))


def _segments(hours: tuple[int, ...]) -> list[tuple[int, int]]:
    """Contiguous (start, end_exclusive) runs of a sorted hour set."""
    runs: list[tuple[int, int]] = []
    start = prev = hours[0]
    for h in hours[1:]:
        if h != prev + 1:
            runs.append((start, prev + 1))
            start = h
        prev = h
    runs.append((start, prev + 1))
    return runs


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
    scheduled: list[tuple[Device, tuple[int, ...], int]] = []  # (device, hours, duration)
    cost_evaluations = 0

    def _placements(device: Device, duration: int,
                    base_net: list[float]) -> list[tuple[int, ...]]:
        """Candidate hour-sets for a device: contiguous windows, plus (for
        interruptible loads like EV chargers) the greedy split placement."""
        options = _contiguous_placements(device, blocked, duration)
        if _is_interruptible(device):
            split = _greedy_interruptible_hours(base_net, device, blocked,
                                                duration, price, sell)
            if split is not None and split not in options:
                options.append(split)
        return options

    # --- Device placement (largest load first) ---
    for device in sorted(profile.devices, key=lambda d: d.kwh, reverse=True):
        duration = _effective_duration(device)
        options = _placements(device, duration, net)
        if not options and duration != device.duration_h:
            # The physical duration does not fit the window/blocks; degrade to
            # the user's declared duration rather than silently dropping.
            duration = device.duration_h
            options = _placements(device, duration, net)
        if not options:
            continue
        costs = {hours: _profile_cost(_add_hours(net, device, hours), price, sell)
                 for hours in options}
        cost_evaluations += len(costs)
        # On a cost tie, pick the placement with the most production surplus:
        # the safest hours against forecast error (the midday peak).
        def _surplus(hours: tuple[int, ...]) -> float:
            return sum(max(-net[h % 24], 0.0) for h in hours)
        best = min(costs, key=lambda hs: (round(costs[hs], 2), -_surplus(hs), hs))
        scheduled.append((device, best, duration))
        net = _add_hours(net, device, best)

    # Greedy is fast but can be locally suboptimal when multiple large loads
    # compete for the same solar window. Coordinate descent rechecks each device
    # against the placement of the others; 24h horizon keeps this cheap.
    for _ in range(3):
        changed = False
        for idx, (device, current_hours, duration) in enumerate(scheduled):
            net_without = _remove_hours(net, device, current_hours)
            options = _placements(device, duration, net_without)
            if not options:
                continue
            costs = {hours: _profile_cost(_add_hours(net_without, device, hours), price, sell)
                     for hours in options}
            cost_evaluations += len(costs)
            best = min(costs, key=lambda hs: (round(costs[hs], 2), -sum(
                max(-net_without[h % 24], 0.0) for h in hs), hs))
            current_cost = _profile_cost(_add_hours(net_without, device, current_hours),
                                         price, sell)
            if round(costs[best], 4) < round(current_cost, 4):
                scheduled[idx] = (device, best, duration)
                net = _add_hours(net_without, device, best)
                changed = True
        if not changed:
            break

    for device, best, duration in scheduled:
        net_without = _remove_hours(net, device, best)
        # Habit reference stays CONTIGUOUS (that is how people actually run
        # devices today: plug the EV in at 19:00 and leave it).
        ref_starts = _valid_starts(device, blocked, duration)
        if not ref_starts:
            continue
        ref_start = reference_hour if reference_hour in ref_starts else max(
            ref_starts,
            key=lambda s: _profile_cost(
                _add_hours(net_without, device, tuple(range(s, s + duration))), price, sell),
        )
        ref_hours = tuple(range(ref_start, ref_start + duration))
        best_cost = _profile_cost(_add_hours(net_without, device, best), price, sell)
        ref_cost = _profile_cost(_add_hours(net_without, device, ref_hours), price, sell)
        cost_evaluations += 2
        saving = max(ref_cost - best_cost, 0.0)
        u = config.SAVING_UNCERTAINTY

        # One PlanItem per contiguous segment; savings split pro-rata by hours.
        segments = _segments(best)
        for seg_no, (seg_start, seg_end) in enumerate(segments, start=1):
            share = (seg_end - seg_start) / len(best)
            name = device.name if len(segments) == 1 else f"{device.name} ({seg_no}. bölüm)"
            items.append(PlanItem(
                type="device", name=name,
                start_h=seg_start,
                end_h=seg_end % 24,
                saving_tl_min=round(saving * share * (1 - u), 2),
                saving_tl_max=round(saving * share * (1 + u), 2),
                reason_code=_reason(seg_start, production.hourly_kwh,
                                    consumption.hourly_kwh, tariff.band),
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
                "device_optimizer": "greedy+coordinate_descent+interruptible",
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
