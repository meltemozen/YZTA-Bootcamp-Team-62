"""Proactive alert generator — agent behaviour triggered WITHOUT the user asking.

The mobile app calls this endpoint periodically (or it is scheduled on the
server) and turns the returned alerts into local notifications. The rules are
deterministic; the wording is a short template (no LLM needed — zero cost).

Alert text is Turkish because it is shown to the user.
"""

from datetime import date, timedelta

from .. import config
from ..schemas import HouseholdProfile
from ..tools import forecast_consumption, forecast_production, get_tariff, get_weather, optimize


def notifications(profile: HouseholdProfile) -> list[dict]:
    tomorrow = date.today() + timedelta(days=1)
    weather = get_weather(profile.lat, profile.lon, tomorrow)
    production = forecast_production(weather, profile.panel_kw)
    consumption = forecast_consumption(profile, tomorrow)
    tariff = get_tariff(
        tomorrow,
        profile.user_type,
        profile.tariff_type,
        monthly_kwh=profile.monthly_bill_kwh,
        custom=profile.custom_tariff,
        require_user_prices=True,
    )
    plan = optimize(production, consumption, tariff, profile)
    alerts = []

    # 0) Regulatory alert: residential rooftop PV net-metering limit is 10 kW
    if profile.user_type == "home" and profile.panel_kw > config.RESIDENTIAL_NETMETER_LIMIT_KW:
        alerts.append({
            "type": "regulation",
            "title": "Panel gücün mahsuplaşma sınırının üstünde",
            "text": f"Mesken aboneliklerinde saatlik mahsuplaşma {config.RESIDENTIAL_NETMETER_LIMIT_KW:.0f} kW'a "
                    "kadar geçerli. Kurulumunun kapsamını görevli tedarik şirketinle teyit et.",
        })

    # 1) The notification repeats the optimizer's actual device decision.
    device_item = next((item for item in plan.items if item.type == "device"), None)
    if device_item:
        alerts.append({
            "type": "daily_plan",
            "title": "Yarın için enerji planın hazır",
            "text": f"{device_item.name}: {device_item.start_h:02d}:00-"
                    f"{device_item.end_h:02d}:00. Beklenen üretim "
                    f"{production.total_kwh:.0f} kWh.",
        })

    # 2) Low production + three-zone tariff → peak alert
    if production.total_kwh < consumption.total_kwh * 0.3 and profile.tariff_type == "three_zone":
        alerts.append({
            "type": "peak_alert",
            "title": "Yarın üretim zayıf",
            "text": "Bulutlu görünüyor; 17:00-22:00 puant diliminde büyük cihaz çalıştırmamaya çalış, "
                    "gece 22:00 sonrası en ucuz dilim.",
        })

    # 3) Battery reminders also come from the actual dispatch plan.
    charge_item = next((item for item in plan.items if item.type == "battery_charge"), None)
    if charge_item:
        alerts.append({
            "type": "battery",
            "title": "Batarya planın hazır",
            "text": f"Şarj aralığı {charge_item.start_h:02d}:00-"
                    f"{charge_item.end_h:02d}:00 olarak planlandı.",
        })
    # 4) Hourly net-metering awareness (single-rate: a once-a-month hint)
    if profile.tariff_type == "single" and production.total_kwh > consumption.total_kwh * 1.2:
        gap = tariff.hourly_price[12] - tariff.hourly_sell_price[12]
        alerts.append({
            "type": "netmeter_hint",
            "title": "Fazla üretimini aynı saatte tüket",
            "text": "Mahsuplaşma artık saatlik: şebekeye sattığın her kWh'te "
                    f"~{gap:.2f} TL kaybediyorsun. Cihazlarını güneş saatine almak birebir kazanç.",
        })

    return alerts
