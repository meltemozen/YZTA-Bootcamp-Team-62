"""uretim_tahmin tool'u — saatlik PV üretim tahmini.

v0: fiziksel model (ışınım × kapasite × performans oranı, sıcaklık düzeltmeli).
Günlük toplamda tipik hata ±%10-15; ürünü bugün çalıştırır.

VB EKİBİ İÇİN: LightGBM modeli hazır olduğunda `uretim_tahmin` içindeki
hesabı değiştirin, imzaya ve UretimTahmini şemasına DOKUNMAYIN
(model_surumu alanını 'v1-lightgbm' yapın). Eğitim verisi için
data/scripts/pvgis_cek.py kullanın.
"""

from datetime import date

from .. import config
from ..schemas import HavaDurumu, UretimTahmini


def uretim_tahmin(hava: HavaDurumu, panel_kw: float) -> UretimTahmini:
    saatlik = []
    for isinim, sicaklik in zip(hava.isinim_wm2, hava.sicaklik_c):
        # Hücre sıcaklığı hava sıcaklığından yüksektir; 25°C üstü her derece güç düşürür
        hucre_sicaklik = sicaklik + config.PV_NOCT_FAKTORU * isinim
        sicaklik_katsayi = 1 - config.PV_SICAKLIK_KATSAYISI * max(0.0, hucre_sicaklik - 25)
        kw = (isinim / 1000.0) * panel_kw * config.PV_PERFORMANS_ORANI * sicaklik_katsayi
        saatlik.append(round(min(max(kw, 0.0), panel_kw), 3))

    return UretimTahmini(
        tarih=hava.tarih,
        saatlik_kwh=saatlik,
        toplam_kwh=round(sum(saatlik), 2),
        model_surumu="v0-fiziksel",
    )


def uretim_tahmin_gun(enlem: float, boylam: float, tarih: date, panel_kw: float) -> UretimTahmini:
    """Agent'ın tek çağrıda kullanacağı kolaylık sarmalayıcısı."""
    from .hava import hava_getir
    return uretim_tahmin(hava_getir(enlem, boylam, tarih), panel_kw)
