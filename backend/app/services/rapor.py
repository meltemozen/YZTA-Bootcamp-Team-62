"""Ay sonu raporu — kanıtlanmış değer katmanı.

Karşı-olgusal hesap DÜRÜSTÇE çerçevelenir: "uygulandı" işaretlenen
önerilerin tasarrufu 'gerçekleşen', işaretlenmeyenlerinki 'kaçırılan
fırsat' olarak raporlanır. Her iki rakam da optimizasyon simülasyonuna
dayanır (sayaç ölçümü değildir) ve açıklama metninde bu belirtilir.
"""

from .. import config, db
from ..schemas import AylikRapor


def aylik_rapor(kullanici_id: int, ay: str) -> AylikRapor:
    planlar = db.oneriler_ay(kullanici_id, ay)
    geri = db.geribildirimler_ay(kullanici_id, ay)
    uygulanan = {(g["tarih"], g["kalem_ad"]) for g in geri if g["uygulandi"]}

    g_min = g_max = kacirilan = co2 = 0.0
    toplam = uygulanan_sayi = 0

    for plan in planlar:
        for kalem in plan.kalemler:
            if kalem.tur == "batarya_sarj":
                continue
            toplam += 1
            anahtar = (plan.tarih.isoformat(), kalem.ad)
            if anahtar in uygulanan:
                uygulanan_sayi += 1
                g_min += kalem.tasarruf_tl_min
                g_max += kalem.tasarruf_tl_max
            else:
                kacirilan += (kalem.tasarruf_tl_min + kalem.tasarruf_tl_max) / 2
        # CO2'yi gün bazında öz tüketimden say; uygulama oranıyla ölçekle
        co2 += plan.co2_tasarruf_kg

    oran = uygulanan_sayi / toplam if toplam else 0.0
    co2 = round(co2 * max(oran, 0.0), 1)

    if toplam == 0:
        aciklama = "Bu ay henüz öneri üretilmedi. Asistandan bir günlük plan iste."
    elif kacirilan > 0:
        aciklama = (f"Önerilerin {uygulanan_sayi}/{toplam} kadarını uyguladın. Kalanını da "
                    f"uygulasaydın ay sonunda yaklaşık {kacirilan:.0f} TL daha cebinde kalırdı. "
                    "Rakamlar tarife ve üretim tahminine dayalı simülasyondur.")
    else:
        aciklama = ("Tebrikler — bu ay tüm önerileri uyguladın! Rakamlar tarife ve üretim "
                    "tahminine dayalı simülasyondur.")

    return AylikRapor(
        ay=ay,
        uygulanan_oneri=uygulanan_sayi,
        toplam_oneri=toplam,
        gerceklesen_tasarruf_tl_min=round(g_min, 2),
        gerceklesen_tasarruf_tl_max=round(g_max, 2),
        kacirilan_tasarruf_tl=round(kacirilan, 2),
        co2_tasarruf_kg=co2,
        araba_km_esdegeri=round(co2 / config.ARABA_KG_CO2_KM, 1),
        agac_ay_esdegeri=round(co2 / (config.AGAC_KG_CO2_YIL / 12), 1),
        aciklama=aciklama,
    )
