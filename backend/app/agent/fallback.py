"""Rule-based fallback planner.

Keeps the product working when the Gemini key is missing or the API fails:
calls tools in a fixed order and produces a Turkish explanation from templates.
This is NOT an "agent" (the order is hand-wired) — the response is honestly
marked agent_mode='fallback'.

The regex patterns and output strings are Turkish because the user speaks
Turkish; only the code identifiers are English.
"""

import re

from .context import ToolContext

_REASON_TEXT = {
    "solar_surplus": "o saatte güneş üretimi tüketimini karşılıyor",
    "avoid_peak": "17-22 arası puant tarifesinden kaçınıyoruz",
    "cheap_night": "gece tarifesi en ucuz dilim",
    "netmeter_edge": "mahsupta satış fiyatı alıştan düşük, evde tüketmek daha kârlı",
}

_HOUR_PATTERN = re.compile(r"(\d{1,2})[:.]?(\d{2})?\s*(?:'?[dt]en|'?[dt]an)?\s*(sonra|önce|once)", re.IGNORECASE)

_PREFERENCE_HINTS = ("evde yokum", "evde olmuyorum", "misafir", "istemiyorum",
                     "olmaz", "uyuyor", "gürültü", "gurultu", "sonra", "önce", "once")


def _is_preference(message: str) -> bool:
    lower = message.lower()
    return any(hint in lower for hint in _PREFERENCE_HINTS)


def _blocked_hours(message: str) -> list[int]:
    """Simple patterns: '22den sonra olmaz' → block 22..07."""
    match = _HOUR_PATTERN.search(message)
    if not match:
        return []
    hour = int(match.group(1)) % 24
    direction = match.group(3).lower()
    if direction == "sonra":
        return [(hour + i) % 24 for i in range(0, (7 - hour) % 24 or 9)]
    return list(range(0, hour))


def _tl(low: float, high: float) -> str:
    """Readable range; if the ends collapse when rounded, show a single value."""
    if f"{low:.0f}" == f"{high:.0f}":
        return f"~{high:.1f} TL"
    return f"{low:.0f}-{high:.0f} TL"


def reply(context: ToolContext, message: str) -> str:
    day = "tomorrow" if "yarın" in message.lower() or "yarin" in message.lower() else "today"

    blocked = []
    if message and _is_preference(message):
        context.write_memory(message.strip())
        blocked = _blocked_hours(message)

    # Derive blocked hours from stored preferences too
    for pref in context.read_memory():
        blocked += _blocked_hours(pref["text"])

    context.get_weather(day)
    context.forecast_production(day)
    context.forecast_consumption(day)
    context.get_tariff(day)
    summary = context.optimize(day, sorted(set(blocked)) or None)

    if not summary["items"]:
        return ("Bugün için kaydıracak esnek cihaz bulamadım. Ayarlardan çamaşır makinesi, "
                "bulaşık makinesi gibi cihazlarını ekleyebilirsin.")

    lines = []
    for i in summary["items"]:
        if i["type"] == "battery_charge":
            lines.append(f"Bataryayı {i['start']:02d}:00-{i['end']:02d}:00 arası güneşten doldur.")
        elif i["type"] == "battery_discharge":
            lines.append(f"Bataryayı {i['start']:02d}:00'dan itibaren kullan "
                         f"({_tl(*i['saving_tl'])}).")
        else:
            reason = _REASON_TEXT.get(i["reason"], "")
            lines.append(f"{i['name']}: {i['start']:02d}:00'da çalıştır "
                         f"({_tl(*i['saving_tl'])}) — {reason}.")

    low, high = summary["total_saving_tl"]
    car_km = summary.get("env", {}).get("car_km")
    env_suffix = f" ({car_km:.0f} km araba yolculuğuna denk)" if car_km else ""
    header = (f"Günün planı hazır — tahmini {_tl(low, high)} tasarruf, "
              f"{summary['co2_kg']:.1f} kg CO2 önleniyor{env_suffix}.")
    if blocked:
        header += " Tercihlerini dikkate aldım (bazı saatler hariç tutuldu)."
    return header + "\n\n" + "\n".join(f"• {s}" for s in lines)
