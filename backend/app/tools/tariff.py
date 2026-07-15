"""get_tariff tool — price adapter for Turkey tariffs + optional price vectors.

Not a dataset; a public table read from config.py.

Turkey rules (July 2026):
* Residential/commercial SINGLE-rate tariff is tiered → the low/high tier price
  is selected from the user's monthly bill kWh. This is the user's MARGINAL
  price in the saving calculation (shifted load is priced at the top tier).
* Three-zone has no tiers; bands are fixed (06-17 / 17-22 / 22-06).
* HOURLY net-metering (1 May 2026+): intra-hour surplus is bought back at that
  hour's retail price minus distribution fee and taxes (≈ ×NETMETER_SELL_RATIO).
  Since sell < buy every hour, self-consumption is always preferred.
"""

import json
from datetime import date

from .. import config
from ..schemas import Tariff


def time_band(hour: int) -> str:
    if 6 <= hour < 17:
        return "day"
    if 17 <= hour < 22:
        return "peak"
    return "night"


def _external_price_vector(day: date) -> Tariff | None:
    if not config.PRICE_VECTOR_FILE:
        return None
    try:
        with open(config.PRICE_VECTOR_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    prices = [float(x) for x in data.get("hourly_price", [])]
    if len(prices) != 24:
        return None
    sell_raw = data.get("hourly_sell_price")
    sell = ([float(x) for x in sell_raw] if isinstance(sell_raw, list) and len(sell_raw) == 24
            else [round(p * config.NETMETER_SELL_RATIO, 4) for p in prices])
    bands = data.get("band") if isinstance(data.get("band"), list) and len(data["band"]) == 24 else ["dynamic"] * 24
    return Tariff(
        date=day,
        hourly_price=prices,
        hourly_sell_price=sell,
        avg_sell_price=round(sum(sell) / 24, 4),
        band=bands,
        source=data.get("source", "external-price-vector"),
    )


def get_tariff(day: date, user_type: str = "home",
               tariff_type: str = "single",
               monthly_kwh: float | None = None) -> Tariff:
    external = _external_price_vector(day)
    if external:
        return external

    group = "residential" if user_type == "home" else "commercial"
    table = config.TARIFF[group]

    if tariff_type == "three_zone":
        prices = [table["three_zone"][time_band(h)] for h in range(24)]
        bands = [time_band(h) for h in range(24)]
    else:
        # Tier: if monthly consumption exceeds threshold, marginal price is high tier
        threshold = table["tier_threshold_kwh_month"]
        unit = (table["single_high"]
                if (monthly_kwh or 0) > threshold else table["single_low"])
        prices = [unit] * 24
        bands = ["flat"] * 24

    sell = [round(p * config.NETMETER_SELL_RATIO, 4) for p in prices]

    return Tariff(
        date=day,
        hourly_price=prices,
        hourly_sell_price=sell,
        avg_sell_price=round(sum(sell) / 24, 4),  # back-compat: average
        band=bands,
        source=f"turkey-regulated-{tariff_type}",
    )
