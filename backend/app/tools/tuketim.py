"""tuketim_tahmin tool'u — saatlik baz yük tahmini (esnek cihazlar hariç).

Yöntem (docs/METHOD.md'de gerekçeli anlatım):
1. Normalize saatlik ŞEKİL: hane profil şablonu (UCI/London literatür şekli,
   Türkiye akşam pikine kaydırılmış) veya işyeri mesai şekli.
2. ÖLÇEK: kullanıcının fatura kWh'i → günlük kWh; mevsim düzeltmesi.
3. Esnek cihazların payı baz yükten DÜŞÜLÜR — onları optimizer yerleştirir.

Doğruluk ±%20-30'dur; bu belirsizlik kullanıcıya TL aralığı olarak yansır
(config.TASARRUF_BELIRSIZLIK). VB ekibi v1'de LightGBM ile şekli
iyileştirir; imza ve şema sabittir.
"""

import math
from datetime import date

from ..schemas import HaneProfili, TuketimTahmini

# Normalize saatlik şekiller (toplamları 1.0) — kaynak: hane tüketim
# literatürü şekli, TR akşam piki (19-22) belirginleştirilmiş.
_EV_SEKLI = [
    0.028, 0.024, 0.022, 0.021, 0.022, 0.026,   # 00-05 gece taban
    0.034, 0.042, 0.044, 0.042, 0.040, 0.040,   # 06-11 sabah
    0.042, 0.042, 0.041, 0.042, 0.046, 0.056,   # 12-17 öğleden sonra
    0.068, 0.078, 0.080, 0.074, 0.058, 0.048,   # 18-23 akşam piki
]

_ISYERI_SEKLI_MESAI = [
    0.012, 0.010, 0.010, 0.010, 0.010, 0.012,   # 00-05 (soğutucu vb. taban)
    0.020, 0.040, 0.075, 0.085, 0.088, 0.088,   # 06-11
    0.085, 0.085, 0.088, 0.088, 0.082, 0.070,   # 12-17
    0.050, 0.035, 0.025, 0.016, 0.014, 0.012,   # 18-23
]


def _mevsim_katsayisi(tarih: date, kullanici_tipi: str) -> float:
    """Yaz klima / kış ısıtma etkisi: ±%15 basit sinüs düzeltmesi."""
    gun_no = tarih.timetuple().tm_yday
    yaz = math.sin(math.pi * (gun_no - 80) / 365)          # Haziran-Ağustos ~1
    return 1.0 + (0.15 if kullanici_tipi == "isyeri" else 0.10) * abs(yaz)


def tuketim_tahmin(profil: HaneProfili, tarih: date) -> TuketimTahmini:
    sekil = _EV_SEKLI if profil.kullanici_tipi == "ev" else _ISYERI_SEKLI_MESAI

    # Esnek cihazların haftalık enerjisini baz yükten düş (haftada ~3 çalıştırma varsayımı)
    esnek_gunluk = sum(c.kwh * 3 / 7 for c in profil.cihazlar)
    gunluk_kwh = max(profil.fatura_kwh_aylik / 30.0 - esnek_gunluk, 1.0)
    gunluk_kwh *= _mevsim_katsayisi(tarih, profil.kullanici_tipi)

    saatlik = [round(gunluk_kwh * pay, 3) for pay in sekil]
    return TuketimTahmini(
        tarih=tarih,
        saatlik_kwh=saatlik,
        toplam_kwh=round(sum(saatlik), 2),
        model_surumu="v0-profil",
    )
