"""Çekirdek mantık testleri: tarife, üretim, tüketim, optimizasyon.

Ağa çıkmaz — hava verisi elle kurulur, davranış deterministiktir.
Çalıştırma: backend/ içinde `python -m pytest tests/ -v`
"""

from datetime import date

import pytest

from app.schemas import Cihaz, HaneProfili, HavaDurumu
from app.tools.optimize import optimize
from app.tools.tarife import saat_dilimi, tarife_getir
from app.tools.tuketim import tuketim_tahmin
from app.tools.uretim import uretim_tahmin

TARIH = date(2026, 7, 15)


def gunesli_hava() -> HavaDurumu:
    """Öğlen tepeli tipik yaz günü."""
    isinim = [0.0] * 24
    for s in range(6, 20):
        isinim[s] = 900 * max(0.0, 1 - abs(s - 13) / 7)
    return HavaDurumu(tarih=TARIH, isinim_wm2=isinim,
                      sicaklik_c=[28.0] * 24, bulutluluk_yuzde=[10.0] * 24)


def profil_olustur(**degisiklik) -> HaneProfili:
    temel = dict(kullanici_tipi="ev", panel_kw=5.0, fatura_kwh_aylik=300,
                 tarife_tipi="tek_zamanli",
                 cihazlar=[Cihaz(ad="Çamaşır makinesi", kwh=1.0, sure_saat=2,
                                 en_erken=8, en_gec=23)])
    temel.update(degisiklik)
    return HaneProfili(**temel)


# --- Tarife ---

def test_saat_dilimleri_epdk_standardi():
    assert saat_dilimi(6) == "gunduz" and saat_dilimi(16) == "gunduz"
    assert saat_dilimi(17) == "puant" and saat_dilimi(21) == "puant"
    assert saat_dilimi(22) == "gece" and saat_dilimi(5) == "gece"


def test_saatlik_mahsup_satis_alistan_dusuk():
    """Saatlik mahsuplaşma (RG 02.04.2026): satış her saatte alıştan düşük —
    öz tüketim önceliğinin ekonomik temeli."""
    for tip in ("tek_zamanli", "uc_zamanli"):
        tarife = tarife_getir(TARIH, "ev", tip, aylik_kwh=300)
        assert all(s < f for s, f in
                   zip(tarife.saatlik_satis_fiyat, tarife.saatlik_fiyat))


def test_mesken_kademe_marjinal_fiyat():
    """EPDK kademeli tarife: 240 kWh/ay üstü tüketen yüksek kademe fiyatı görür."""
    dusuk = tarife_getir(TARIH, "ev", "tek_zamanli", aylik_kwh=200)
    yuksek = tarife_getir(TARIH, "ev", "tek_zamanli", aylik_kwh=350)
    assert yuksek.saatlik_fiyat[0] > dusuk.saatlik_fiyat[0]


def test_uc_zamanli_puant_en_pahali():
    tarife = tarife_getir(TARIH, "ev", "uc_zamanli")
    assert tarife.saatlik_fiyat[19] > tarife.saatlik_fiyat[10] > tarife.saatlik_fiyat[3]


# --- Üretim ---

def test_uretim_gece_sifir_gunduz_pozitif():
    uretim = uretim_tahmin(gunesli_hava(), panel_kw=5.0)
    assert uretim.saatlik_kwh[2] == 0
    assert uretim.saatlik_kwh[13] > 2.5          # öğlen tepe
    assert max(uretim.saatlik_kwh) <= 5.0        # kapasite aşılmaz
    assert uretim.toplam_kwh == pytest.approx(sum(uretim.saatlik_kwh), abs=0.1)


# --- Tüketim ---

def test_tuketim_faturaya_kalibre():
    profil = profil_olustur(cihazlar=[])
    tuketim = tuketim_tahmin(profil, TARIH)
    # Günlük ≈ fatura/30, mevsim katsayısı ±%15 içinde
    assert 300 / 30 * 0.85 <= tuketim.toplam_kwh <= 300 / 30 * 1.20
    # Ev profili akşam piki: 20:00 > 03:00
    assert tuketim.saatlik_kwh[20] > tuketim.saatlik_kwh[3] * 2


# --- Optimizasyon: ürünün kalbi ---

def test_tek_zamanli_cihaz_gunes_saatine_yerlesir():
    """Tek zamanlı (kullanıcıların çoğu): saatlik mahsupta satış kaybı (~×0.7)
    her zaman alıştan ucuz → cihaz güneş fazlası saatine (9-16) yerleşmeli."""
    profil = profil_olustur()
    uretim = uretim_tahmin(gunesli_hava(), profil.panel_kw)
    tuketim = tuketim_tahmin(profil, TARIH)
    tarife = tarife_getir(TARIH, "ev", "tek_zamanli", aylik_kwh=300)

    plan = optimize(uretim, tuketim, tarife, profil)
    cihaz = next(k for k in plan.kalemler if k.tur == "cihaz")
    assert 9 <= cihaz.baslangic_saat <= 16
    assert cihaz.gerekce_kodu in ("gunes_bol", "puant_kacinma")
    assert plan.toplam_tasarruf_tl_max > plan.toplam_tasarruf_tl_min >= 0


def test_uc_zamanli_cihaz_asla_puanta_girmez():
    """Üç zamanlıda gündüz SATIŞ fiyatı gece ALIŞTAN yüksek olabilir → cihaz
    geceye kayabilir (doğru ekonomi); ama 17-22 puanta asla girmemeli."""
    profil = profil_olustur(tarife_tipi="uc_zamanli")
    uretim = uretim_tahmin(gunesli_hava(), profil.panel_kw)
    tuketim = tuketim_tahmin(profil, TARIH)
    tarife = tarife_getir(TARIH, "ev", "uc_zamanli")

    plan = optimize(uretim, tuketim, tarife, profil)
    cihaz = next(k for k in plan.kalemler if k.tur == "cihaz")
    calisma_saatleri = {(cihaz.baslangic_saat + i) % 24 for i in range(2)}
    assert not any(17 <= s < 22 for s in calisma_saatleri)


def test_yasak_saatlere_uyulur():
    """Hafızadaki tercih ('öğlen evde yokum') planı gerçekten değiştirmeli."""
    profil = profil_olustur()
    uretim = uretim_tahmin(gunesli_hava(), profil.panel_kw)
    tuketim = tuketim_tahmin(profil, TARIH)
    tarife = tarife_getir(TARIH, "ev", "uc_zamanli")

    yasak = set(range(9, 18))
    plan = optimize(uretim, tuketim, tarife, profil, yasak_saatler=yasak)
    cihaz = next(k for k in plan.kalemler if k.tur == "cihaz")
    calisma = {(cihaz.baslangic_saat + i) % 24 for i in range(2)}
    assert not calisma & yasak


def test_batarya_gunduz_sarj_puant_desarj():
    profil = profil_olustur(batarya_kwh=5.0, batarya_guc_kw=2.5, fatura_kwh_aylik=250)
    uretim = uretim_tahmin(gunesli_hava(), profil.panel_kw)
    tuketim = tuketim_tahmin(profil, TARIH)
    tarife = tarife_getir(TARIH, "ev", "uc_zamanli")

    plan = optimize(uretim, tuketim, tarife, profil)
    turler = {k.tur for k in plan.kalemler}
    assert "batarya_sarj" in turler and "batarya_desarj" in turler
    sarj = next(k for k in plan.kalemler if k.tur == "batarya_sarj")
    assert 6 <= sarj.baslangic_saat <= 17          # güneşten şarj


def test_oz_tuketim_orani_mantikli():
    profil = profil_olustur()
    uretim = uretim_tahmin(gunesli_hava(), profil.panel_kw)
    tuketim = tuketim_tahmin(profil, TARIH)
    tarife = tarife_getir(TARIH, "ev", "uc_zamanli")
    plan = optimize(uretim, tuketim, tarife, profil)
    assert 0 <= plan.oz_tuketim_orani <= 1
    assert plan.co2_tasarruf_kg > 0
