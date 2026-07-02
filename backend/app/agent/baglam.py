"""Agent araç bağlamı: tool'ları tek kullanıcıya bağlar ve ara sonuçları
saklar. Hem Gemini orkestratörü hem fallback aynı bağlamı kullanır —
"agent modelin çıktısını gerçekten tüketiyor" garantisi budur.
"""

from datetime import date, timedelta

from .. import db
from ..schemas import GunlukPlan, HaneProfili
from ..tools import (hafiza_oku, hafiza_yaz, hava_getir, optimize,
                     tarife_getir, tuketim_tahmin, uretim_tahmin)


def _tarih_coz(metin: str | None) -> date:
    bugun = date.today()
    if not metin or metin in ("bugun", "bugün"):
        return bugun
    if metin in ("yarin", "yarın"):
        return bugun + timedelta(days=1)
    try:
        return date.fromisoformat(metin)
    except ValueError:
        return bugun + timedelta(days=1)


class AracBaglami:
    """Bir istek boyunca yaşar; agent'ın çağırdığı her tool'u loglar."""

    def __init__(self, kullanici_id: int, profil: HaneProfili):
        self.kullanici_id = kullanici_id
        self.profil = profil
        self.cagrilar: list[str] = []
        self.son_plan: GunlukPlan | None = None
        self._hava = {}
        self._uretim = {}
        self._tuketim = {}
        self._tarife = {}

    # --- Agent'a açılan tool yüzeyi (isimler kontrattaki isimlerdir) ---

    def hava_getir(self, tarih: str | None = None) -> dict:
        t = _tarih_coz(tarih)
        self.cagrilar.append(f"hava_getir({t})")
        self._hava[t] = hava_getir(self.profil.enlem, self.profil.boylam, t)
        h = self._hava[t]
        return {"tarih": str(t), "toplam_isinim_kwh_m2": round(sum(h.isinim_wm2) / 1000, 2),
                "maks_sicaklik": max(h.sicaklik_c), "ort_bulutluluk": round(sum(h.bulutluluk_yuzde) / 24, 1)}

    def uretim_tahmin(self, tarih: str | None = None) -> dict:
        t = _tarih_coz(tarih)
        self.cagrilar.append(f"uretim_tahmin({t})")
        if t not in self._hava:
            self._hava[t] = hava_getir(self.profil.enlem, self.profil.boylam, t)
        self._uretim[t] = uretim_tahmin(self._hava[t], self.profil.panel_kw)
        u = self._uretim[t]
        tepe = max(range(24), key=lambda s: u.saatlik_kwh[s])
        return {"tarih": str(t), "toplam_kwh": u.toplam_kwh,
                "tepe_saat": tepe, "tepe_kwh": u.saatlik_kwh[tepe]}

    def tuketim_tahmin(self, tarih: str | None = None) -> dict:
        t = _tarih_coz(tarih)
        self.cagrilar.append(f"tuketim_tahmin({t})")
        self._tuketim[t] = tuketim_tahmin(self.profil, t)
        return {"tarih": str(t), "toplam_kwh": self._tuketim[t].toplam_kwh}

    def tarife_getir(self, tarih: str | None = None) -> dict:
        t = _tarih_coz(tarih)
        self.cagrilar.append(f"tarife_getir({t})")
        self._tarife[t] = tarife_getir(t, self.profil.kullanici_tipi,
                                       self.profil.tarife_tipi,
                                       aylik_kwh=self.profil.fatura_kwh_aylik)
        tf = self._tarife[t]
        return {"tarife_tipi": self.profil.tarife_tipi,
                "en_ucuz_saat_tl": min(tf.saatlik_fiyat), "en_pahali_saat_tl": max(tf.saatlik_fiyat),
                "ort_satis_tl": tf.mahsup_satis_fiyati,
                "not": "Saatlik mahsuplaşma: satış fiyatı her saatte alıştan ~%30 düşük, "
                       "üretimi o saat içinde evde tüketmek satmaktan kârlı."}

    def optimize(self, tarih: str | None = None, yasak_saatler: list[int] | None = None) -> dict:
        t = _tarih_coz(tarih)
        self.cagrilar.append(f"optimize({t})")
        if t not in self._uretim:
            self.uretim_tahmin(str(t))
        if t not in self._tuketim:
            self.tuketim_tahmin(str(t))
        if t not in self._tarife:
            self.tarife_getir(str(t))
        plan = optimize(self._uretim[t], self._tuketim[t], self._tarife[t],
                        self.profil, set(yasak_saatler or []))
        self.son_plan = plan
        db.oneri_kaydet(self.kullanici_id, plan)
        return {
            "tarih": str(t),
            "kalemler": [{"ad": k.ad, "tur": k.tur, "baslangic": k.baslangic_saat,
                          "bitis": k.bitis_saat, "tasarruf_tl": [k.tasarruf_tl_min, k.tasarruf_tl_max],
                          "gerekce": k.gerekce_kodu} for k in plan.kalemler],
            "toplam_tasarruf_tl": [plan.toplam_tasarruf_tl_min, plan.toplam_tasarruf_tl_max],
            "co2_kg": plan.co2_tasarruf_kg,
            "cevre": plan.ozet_veri.get("cevre", {}),
            "oz_tuketim_orani": plan.oz_tuketim_orani,
        }

    def hafiza_oku(self) -> list[dict]:
        self.cagrilar.append("hafiza_oku")
        return hafiza_oku(self.kullanici_id)

    def hafiza_yaz(self, metin: str) -> dict:
        self.cagrilar.append(f"hafiza_yaz({metin[:40]})")
        return hafiza_yaz(self.kullanici_id, metin, kaynak="cikarim")
