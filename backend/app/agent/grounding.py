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
