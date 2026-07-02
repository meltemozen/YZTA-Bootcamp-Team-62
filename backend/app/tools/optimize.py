"""optimize tool'u — cihaz + batarya günlük planı.

Karar mantığı (deterministik ve açıklanabilir — jüri sorusu "neden 13:00?"
buradan cevaplanır):

* Her saat için net yük = baz tüketim − üretim.
* İthal edilen kWh alış fiyatından, ihraç edilen kWh MAHSUP satış
  fiyatından değerlenir. Satış fiyatı < alış fiyatı olduğundan üretimi
  evde tüketmek (öz tüketim) her zaman şebekeye satmaktan kârlıdır —
  Türkiye mahsuplaşma mevzuatının plana yansıdığı yer burasıdır.
* Cihazlar büyükten küçüğe, uygun saat pencereleri içinde toplam maliyeti
  en aza indiren başlangıç saatine yerleştirilir (kapsamlı tarama, 24 saat).
* Tasarruf, "alışkanlık saati" referansına göre hesaplanır (ev: 19:00
  akşam piki, işyeri: mesai başı) ve tüketim belirsizliği nedeniyle
  ARALIK olarak raporlanır.
* Batarya: üretim fazlası saatlerde şarj, en pahalı ithalat saatlerinde
  deşarj (%90 tur verimi).
"""

from datetime import date

from .. import config
from ..schemas import (Cihaz, GunlukPlan, HaneProfili, PlanKalemi,
                       TarifeBilgisi, TuketimTahmini, UretimTahmini)


def _profil_maliyeti(net: list[float], fiyat: list[float], satis: list[float]) -> float:
    """Günlük TL maliyet — SAATLİK mahsuplaşma (RG 02.04.2026):
    her saat ayrı netleşir; ithalat o saatin alış, ihracat o saatin satış
    fiyatından değerlenir."""
    toplam = 0.0
    for saat in range(24):
        if net[saat] > 0:
            toplam += net[saat] * fiyat[saat]
        else:
            toplam -= (-net[saat]) * satis[saat]
    return toplam


def _cihaz_ekle(net: list[float], cihaz: Cihaz, baslangic: int) -> list[float]:
    yeni = net[:]
    saatlik = cihaz.kwh / cihaz.sure_saat
    for i in range(cihaz.sure_saat):
        yeni[(baslangic + i) % 24] += saatlik
    return yeni


def _uygun_baslangiclar(cihaz: Cihaz, yasak: set[int]) -> list[int]:
    adaylar = []
    for s in range(24):
        bitis = s + cihaz.sure_saat - 1
        if s < cihaz.en_erken or bitis > cihaz.en_gec:
            continue
        if any((s + i) % 24 in yasak for i in range(cihaz.sure_saat)):
            continue
        adaylar.append(s)
    return adaylar


def _gerekce(baslangic: int, uretim: list[float], tuketim: list[float],
             dilimler: list[str]) -> str:
    if uretim[baslangic] > tuketim[baslangic]:
        return "gunes_bol"
    if dilimler[baslangic] == "gece":
        return "gece_ucuz"
    if dilimler[(baslangic + 23) % 24] == "puant" or dilimler[baslangic] != "puant":
        return "puant_kacinma"
    return "mahsup_avantaji"


def optimize(uretim: UretimTahmini, tuketim: TuketimTahmini,
             tarife: TarifeBilgisi, profil: HaneProfili,
             yasak_saatler: set[int] | None = None) -> GunlukPlan:
    yasak = yasak_saatler or set()
    fiyat, satis = tarife.saatlik_fiyat, tarife.saatlik_satis_fiyat
    net = [t - u for t, u in zip(tuketim.saatlik_kwh, uretim.saatlik_kwh)]

    kalemler: list[PlanKalemi] = []
    referans_saat = 19 if profil.kullanici_tipi == "ev" else profil.mesai_baslangic

    # --- Cihaz yerleştirme (büyük yük önce) ---
    for cihaz in sorted(profil.cihazlar, key=lambda c: c.kwh, reverse=True):
        adaylar = _uygun_baslangiclar(cihaz, yasak)
        if not adaylar:
            continue
        maliyetler = {s: _profil_maliyeti(_cihaz_ekle(net, cihaz, s), fiyat, satis)
                      for s in adaylar}
        # Maliyet eşitliğinde üretim fazlası en bol pencereyi seç: tahmin
        # hatasına karşı en güvenli saat (öğlen tepesi) tercih edilir.
        def _fazla(s: int) -> float:
            return sum(max(-net[(s + i) % 24], 0.0) for i in range(cihaz.sure_saat))
        en_iyi = min(maliyetler, key=lambda s: (round(maliyetler[s], 2), -_fazla(s)))

        ref = referans_saat if referans_saat in maliyetler else max(maliyetler, key=maliyetler.get)
        tasarruf = max(maliyetler[ref] - maliyetler[en_iyi], 0.0)
        b = config.TASARRUF_BELIRSIZLIK

        kalemler.append(PlanKalemi(
            tur="cihaz", ad=cihaz.ad,
            baslangic_saat=en_iyi,
            bitis_saat=(en_iyi + cihaz.sure_saat) % 24,
            tasarruf_tl_min=round(tasarruf * (1 - b), 2),
            tasarruf_tl_max=round(tasarruf * (1 + b), 2),
            gerekce_kodu=_gerekce(en_iyi, uretim.saatlik_kwh, tuketim.saatlik_kwh,
                                  tarife.dilim_adi),
        ))
        net = _cihaz_ekle(net, cihaz, en_iyi)

    # --- Batarya: fazla üretimle şarj, pahalı saatte deşarj ---
    if profil.batarya_kwh > 0 and profil.batarya_guc_kw > 0:
        verim = 0.90
        sarj_saatleri = sorted((s for s in range(24) if net[s] < 0),
                               key=lambda s: net[s])  # en çok fazla olan önce
        depolanan, sarj_pencere = 0.0, []
        for s in sarj_saatleri:
            if depolanan >= profil.batarya_kwh * 0.95:
                break
            alinan = min(-net[s], profil.batarya_guc_kw,
                         profil.batarya_kwh * 0.95 - depolanan)
            if alinan <= 0.05:
                continue
            net[s] += alinan
            depolanan += alinan
            sarj_pencere.append(s)

        desarj_saatleri = sorted((s for s in range(24) if net[s] > 0),
                                 key=lambda s: fiyat[s], reverse=True)
        kazanc, desarj_pencere = 0.0, []
        kullanilabilir = depolanan * verim
        ort_satis = sum(satis) / 24
        for s in desarj_saatleri:
            if kullanilabilir <= 0.05:
                break
            verilen = min(net[s], profil.batarya_guc_kw, kullanilabilir)
            net[s] -= verilen
            kullanilabilir -= verilen
            # Kazanç: şebekeden almaktan kurtulunan − mahsupta satılsaydı geliri
            kazanc += verilen * fiyat[s] - (verilen / verim) * ort_satis
            desarj_pencere.append(s)

        if sarj_pencere and desarj_pencere:
            b = config.TASARRUF_BELIRSIZLIK
            kalemler.append(PlanKalemi(
                tur="batarya_sarj", ad="Batarya",
                baslangic_saat=min(sarj_pencere), bitis_saat=max(sarj_pencere) + 1,
                tasarruf_tl_min=0, tasarruf_tl_max=0, gerekce_kodu="gunes_bol"))
            kalemler.append(PlanKalemi(
                tur="batarya_desarj", ad="Batarya",
                baslangic_saat=min(desarj_pencere), bitis_saat=max(desarj_pencere) + 1,
                tasarruf_tl_min=round(max(kazanc, 0) * (1 - b), 2),
                tasarruf_tl_max=round(max(kazanc, 0) * (1 + b), 2),
                gerekce_kodu="puant_kacinma"))

    # --- Özet metrikler ---
    oz_tuketim = sum(min(u, u + n) if n < 0 else u
                     for u, n in zip(uretim.saatlik_kwh, net))
    oz_oran = round(min(oz_tuketim / uretim.toplam_kwh, 1.0), 2) if uretim.toplam_kwh > 0 else 0.0
    co2 = round(oz_tuketim * config.CO2_KG_PER_KWH, 2)

    return GunlukPlan(
        tarih=uretim.tarih,
        kalemler=kalemler,
        toplam_tasarruf_tl_min=round(sum(k.tasarruf_tl_min for k in kalemler), 2),
        toplam_tasarruf_tl_max=round(sum(k.tasarruf_tl_max for k in kalemler), 2),
        co2_tasarruf_kg=co2,
        oz_tuketim_orani=oz_oran,
        ozet_veri={
            "uretim": uretim.saatlik_kwh,
            "tuketim": tuketim.saatlik_kwh,
            "fiyat": tarife.saatlik_fiyat,
            "dilim": tarife.dilim_adi,
            # Çevresel eşdeğerler: CO2'yi somutlaştırır (ETKB EF + genel
            # kabul görmüş eşdeğerler, kaynaklar config.py'de)
            "cevre": {
                "araba_km": round(co2 / config.ARABA_KG_CO2_KM, 1),
                "agac_gun": round(co2 / (config.AGAC_KG_CO2_YIL / 365), 1),
            },
        },
    )
