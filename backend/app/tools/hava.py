"""hava_getir tool'u — Open-Meteo canlı hava/ışınım verisi.

API anahtarı gerektirmez. Hem agent'ın canlı tool'u hem de (geçmiş uç
noktasıyla) VB ekibinin model eğitim verisi kaynağıdır.
Ağ hatasında son başarılı yanıt önbellekten döner; o da yoksa mevsimsel
sentetik profil üretilir ki ürün asla boş ekran göstermesin.
"""

import json
import logging
import math
import os
import tempfile
from datetime import date

import httpx

from ..schemas import HavaDurumu

log = logging.getLogger(__name__)

_ONBELLEK = os.path.join(tempfile.gettempdir(), "voltaic_hava_cache.json")
_URL = "https://api.open-meteo.com/v1/forecast"


def _onbellege_yaz(anahtar: str, veri: dict) -> None:
    try:
        mevcut = {}
        if os.path.exists(_ONBELLEK):
            with open(_ONBELLEK, encoding="utf-8") as f:
                mevcut = json.load(f)
        mevcut[anahtar] = veri
        with open(_ONBELLEK, "w", encoding="utf-8") as f:
            json.dump(mevcut, f)
    except OSError:
        pass


def _onbellekten_oku(anahtar: str) -> dict | None:
    try:
        with open(_ONBELLEK, encoding="utf-8") as f:
            return json.load(f).get(anahtar)
    except (OSError, json.JSONDecodeError):
        return None


def _sentetik(tarih: date) -> dict:
    """Ağ tamamen yoksa: mevsime göre kaba temiz-gökyüzü profili."""
    gun_no = tarih.timetuple().tm_yday
    mevsim = math.sin(math.pi * (gun_no - 80) / 365)  # yaz ortası ~1
    tepe = 550 + 400 * max(mevsim, 0)
    isinim = [max(0.0, tepe * math.sin(math.pi * (s - 5.5) / 13)) if 6 <= s <= 19 else 0.0
              for s in range(24)]
    sicaklik = [12 + 12 * max(mevsim, 0) + 6 * math.sin(math.pi * (s - 9) / 12) for s in range(24)]
    return {"isinim": isinim, "sicaklik": sicaklik, "bulut": [20.0] * 24}


def hava_getir(enlem: float, boylam: float, tarih: date) -> HavaDurumu:
    anahtar = f"{enlem:.2f},{boylam:.2f},{tarih.isoformat()}"
    try:
        yanit = httpx.get(_URL, params={
            "latitude": enlem,
            "longitude": boylam,
            "hourly": "shortwave_radiation,temperature_2m,cloud_cover",
            "start_date": tarih.isoformat(),
            "end_date": tarih.isoformat(),
            "timezone": "Europe/Istanbul",
        }, timeout=15)
        yanit.raise_for_status()
        saatlik = yanit.json()["hourly"]
        veri = {
            "isinim": saatlik["shortwave_radiation"][:24],
            "sicaklik": saatlik["temperature_2m"][:24],
            "bulut": saatlik["cloud_cover"][:24],
        }
        _onbellege_yaz(anahtar, veri)
    except (httpx.HTTPError, KeyError) as hata:
        log.warning("Open-Meteo erişilemedi (%s), önbellek/sentetik kullanılacak", hata)
        veri = _onbellekten_oku(anahtar) or _sentetik(tarih)

    return HavaDurumu(
        tarih=tarih,
        isinim_wm2=[float(x or 0) for x in veri["isinim"]],
        sicaklik_c=[float(x or 15) for x in veri["sicaklik"]],
        bulutluluk_yuzde=[float(x or 0) for x in veri["bulut"]],
    )
