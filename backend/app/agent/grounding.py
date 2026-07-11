"""Grounding guard — programmatic enforcement of the honesty rule.

The product's core promise (docs/METHOD.md) is that the agent NEVER states a
number that did not come from a tool output. LLMs hallucinate figures, so we
verify the generated Turkish reply against the plan the tools actually produced.

`ungrounded_numbers(reply, plan)` returns the numbers in the reply that are NOT
backed by the plan (within rounding tolerance). Small integers 0–24 are treated
as clock hours / counts and ignored; values ≥ 1000 (years, ids) are ignored.

Used by:
  * the agent test suite (asserts fallback replies are grounded), and
  * the orchestrator (logs a warning when the live LLM invents a figure — the
    hook where Sprint-2 "regenerate on ungrounded" plugs in).
"""

import re

from ..schemas import DailyPlan

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def extract_numbers(text: str) -> list[float]:
    """All decimal numbers in a string (comma or dot decimal separator)."""
    return [float(m.replace(",", ".")) for m in _NUMBER.findall(text)]


def grounded_values(plan: DailyPlan) -> set[float]:
    """Every figure a truthful reply about this plan could legitimately mention."""
    values: set[float] = set()

    def add(x: float) -> None:
        values.add(round(float(x), 2))
        values.add(float(round(x)))

    for item in plan.items:
        add(item.start_h)
        add(item.end_h)
        add(item.saving_tl_min)
        add(item.saving_tl_max)
    add(plan.total_saving_tl_min)
    add(plan.total_saving_tl_max)
    add(plan.co2_saved_kg)
    add(plan.self_consumption_ratio * 100)
    env = plan.chart_data.get("env", {})
    for key in ("car_km", "tree_days"):
        if key in env:
            add(env[key])
    return values


def ungrounded_numbers(reply: str, plan: DailyPlan, *,
                       tol_abs: float = 0.6, tol_rel: float = 0.04) -> list[float]:
    """Numbers in `reply` not backed by `plan` (within tolerance).

    An empty list means the reply is fully grounded.
    """
    allowed = grounded_values(plan)
    bad: list[float] = []
    for n in extract_numbers(reply):
        # Clock hours / small counts (0–24) and years/ids (>= 1000) are ignored.
        if (0 <= n <= 24 and n == int(n)) or n >= 1000:
            continue
        if any(abs(n - a) <= max(tol_abs, tol_rel * abs(a)) for a in allowed):
            continue
        bad.append(n)
    return bad


# A schedule built purely from hour values (e.g. "bataryanı 02-06 arası şarj et")
# passes `ungrounded_numbers` untouched, because clock hours 0-24 are deliberately
# excluded from that check. These two guards close that gap for the two entity
# classes known to be fabricated this way: a nonexistent battery, and a date the
# agent could not actually resolve.

_BATTERY_KEYWORDS = ("batarya", "akü", "pil")
_DEVICE_KEYWORDS = ("çamaşır", "bulaşık", "kurutma", "klima", "su ısıtıcı", "termosifon",
                    "elektrikli araç", "şofben")

_TR_WEEKDAYS = ("pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar")
_DATE_HEDGE_PHRASES = ("net çözemedim", "netleştir", "emin olamadım", "tam anlayamadım", "varsaydım")


def ungrounded_entities(reply: str, plan: DailyPlan) -> list[str]:
    """Device/battery mentions in `reply` for something the plan doesn't contain.

    Returns the offending keyword(s); empty means every entity mentioned is
    backed by an actual `plan.items` entry.
    """
    reply_l = reply.lower()
    bad: list[str] = []

    has_battery_item = any(i.type.startswith("battery") for i in plan.items)
    if not has_battery_item and any(k in reply_l for k in _BATTERY_KEYWORDS):
        bad.append("batarya")

    item_names = " ".join(i.name.lower() for i in plan.items if i.type == "device")
    for keyword in _DEVICE_KEYWORDS:
        if keyword in reply_l and keyword not in item_names:
            bad.append(keyword)

    return bad


def ungrounded_dates(reply: str, plan: DailyPlan) -> list[str]:
    """Turkish weekday names in `reply` that contradict the plan's real date.

    `context._resolve_date` only understands today/tomorrow/ISO — a weekday
    name like "salı" silently falls back to tomorrow, but the LLM may still
    echo the user's word back as if it had been honoured. A reply that
    explicitly hedges about the date (per the system prompt's disclosure
    rule) is not flagged, since naming the unresolved day there is expected.
    """
    reply_l = reply.lower()
    if any(phrase in reply_l for phrase in _DATE_HEDGE_PHRASES):
        return []

    actual = _TR_WEEKDAYS[plan.date.weekday()]
    return [w for w in _TR_WEEKDAYS if w != actual and re.search(rf"\b{w}\b", reply_l)]
