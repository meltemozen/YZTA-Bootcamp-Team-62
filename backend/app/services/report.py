"""Monthly report — the proven-value layer.

The counterfactual is framed HONESTLY: the saving of items marked "applied" is
reported as 'realized', the rest as 'missed opportunity'. Both figures rest on
the optimization simulation (not meter readings) and the note text says so.
"""

from .. import config, db
from ..schemas import MonthlyReport


def monthly_report(user_id: int, month: str) -> MonthlyReport:
    plans = db.plans_for_month(user_id, month)
    feedback = db.feedback_for_month(user_id, month)
    applied = {(f["date"], f["item_name"]) for f in feedback if f["applied"]}

    realized_min = realized_max = missed = co2 = 0.0
    total = applied_count = 0

    for plan in plans:
        for item in plan.items:
            if item.type == "battery_charge":
                continue
            total += 1
            key = (plan.date.isoformat(), item.name)
            if key in applied:
                applied_count += 1
                realized_min += item.saving_tl_min
                realized_max += item.saving_tl_max
            else:
                missed += (item.saving_tl_min + item.saving_tl_max) / 2
        # Count CO2 daily from self-consumption; scale by application rate
        co2 += plan.co2_saved_kg

    ratio = applied_count / total if total else 0.0
    co2 = round(co2 * max(ratio, 0.0), 1)

    if total == 0:
        note = "Bu ay henüz öneri üretilmedi. Asistandan bir günlük plan iste."
    elif missed > 0:
        note = (f"Önerilerin {applied_count}/{total} kadarını uyguladın. Kalanını da "
                f"uygulasaydın ay sonunda yaklaşık {missed:.0f} TL daha cebinde kalırdı. "
                "Rakamlar tarife ve üretim tahminine dayalı simülasyondur.")
    else:
        note = ("Tebrikler — bu ay tüm önerileri uyguladın! Rakamlar tarife ve üretim "
                "tahminine dayalı simülasyondur.")

    return MonthlyReport(
        month=month,
        applied_count=applied_count,
        total_count=total,
        realized_saving_tl_min=round(realized_min, 2),
        realized_saving_tl_max=round(realized_max, 2),
        missed_saving_tl=round(missed, 2),
        co2_saved_kg=co2,
        car_km_equiv=round(co2 / config.CAR_KG_CO2_KM, 1),
        tree_month_equiv=round(co2 / (config.TREE_KG_CO2_YEAR / 12), 1),
        note=note,
    )
