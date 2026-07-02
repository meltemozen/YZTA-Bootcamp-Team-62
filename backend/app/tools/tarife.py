"""tarife_getir tool'u — EPDK tarife + saatlik mahsuplaşma satış fiyatı.

Veri seti değildir; kamuya açık tablo config.py'den okunur.

Türkiye kuralları (Temmuz 2026):
* Mesken/ticarethane TEK ZAMANLI tarife kademelidir → kullanıcının aylık
  fatura kWh'ine göre düşük/yüksek kademe fiyatı seçilir. Bu, tasarruf
  hesabında kullanıcının MARJİNAL fiyatıdır (kaydırılan yük en üst kademeden
  fiyatlanır).
* Üç zamanlıda kademe yoktur; dilimler sabittir (06-17 / 17-22 / 22-06).
* SAATLİK mahsuplaşma (1 Mayıs 2026+): saat içi fazla üretim, o saatin
  perakende fiyatından dağıtım bedeli ve vergiler düşülerek satın alınır
  (≈ ×MAHSUP_SATIS_ORANI). Satış her saatte alıştan ucuz olduğu için öz
  tüketim her zaman önceliklidir.
"""

from datetime import date

from .. import config
from ..schemas import TarifeBilgisi


def saat_dilimi(saat: int) -> str:
    if 6 <= saat < 17:
        return "gunduz"
    if 17 <= saat < 22:
        return "puant"
    return "gece"


def tarife_getir(tarih: date, kullanici_tipi: str = "ev",
                 tarife_tipi: str = "tek_zamanli",
                 aylik_kwh: float | None = None) -> TarifeBilgisi:
    grup = "mesken" if kullanici_tipi == "ev" else "isyeri"
    tablo = config.TARIFE[grup]

    if tarife_tipi == "uc_zamanli":
        fiyatlar = [tablo["uc_zamanli"][saat_dilimi(s)] for s in range(24)]
        dilimler = [saat_dilimi(s) for s in range(24)]
    else:
        # Kademe: aylık tüketim eşiği aşıyorsa marjinal fiyat yüksek kademedir
        esik = tablo["kademe_esik_kwh_ay"]
        birim = (tablo["tek_zamanli_yuksek"]
                 if (aylik_kwh or 0) > esik else tablo["tek_zamanli_dusuk"])
        fiyatlar = [birim] * 24
        dilimler = ["tek"] * 24

    satis = [round(f * config.MAHSUP_SATIS_ORANI, 4) for f in fiyatlar]

    return TarifeBilgisi(
        tarih=tarih,
        saatlik_fiyat=fiyatlar,
        saatlik_satis_fiyat=satis,
        mahsup_satis_fiyati=round(sum(satis) / 24, 4),  # geriye uyum: ortalama
        dilim_adi=dilimler,
    )
