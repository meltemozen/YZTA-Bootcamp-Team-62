"""Proaktif uyarı üretici — kullanıcı SORMADAN tetiklenen agent davranışı.

Mobil uygulama bu ucu periyodik çağırır (veya sunucuda zamanlanır) ve
dönen uyarıları yerel bildirime çevirir. Kurallar deterministiktir;
metinleştirme kısa şablondur (LLM'e gerek yok — maliyet sıfır).
"""

from datetime import date, timedelta

from .. import config
from ..schemas import HaneProfili
from ..tools import hava_getir, tarife_getir, tuketim_tahmin, uretim_tahmin


def bildirimler(profil: HaneProfili) -> list[dict]:
    yarin = date.today() + timedelta(days=1)
    hava = hava_getir(profil.enlem, profil.boylam, yarin)
    uretim = uretim_tahmin(hava, profil.panel_kw)
    tuketim = tuketim_tahmin(profil, yarin)
    uyarilar = []

    # 0) Mevzuat uyarısı: mesken çatı GES mahsuplaşma sınırı 10 kW
    if profil.kullanici_tipi == "ev" and profil.panel_kw > config.MESKEN_MAHSUP_LIMIT_KW:
        uyarilar.append({
            "tur": "mevzuat",
            "baslik": "Panel gücün mahsuplaşma sınırının üstünde",
            "metin": f"Mesken aboneliklerinde saatlik mahsuplaşma {config.MESKEN_MAHSUP_LIMIT_KW:.0f} kW'a "
                     "kadar geçerli. Kurulumunun kapsamını görevli tedarik şirketinle teyit et.",
        })

    # 1) Yarın üretim belirgin biçimde yüksek → esnek yükleri yarına kaydır
    if uretim.toplam_kwh > tuketim.toplam_kwh * 0.8 and profil.cihazlar:
        tepe = max(range(24), key=lambda s: uretim.saatlik_kwh[s])
        uyarilar.append({
            "tur": "gunes_firsati",
            "baslik": "Yarın güneş bol ☀️",
            "metin": f"Yarın ~{uretim.toplam_kwh:.0f} kWh üretim bekleniyor (tepe {tepe:02d}:00). "
                     f"{profil.cihazlar[0].ad} gibi cihazları öğlen saatlerine planla.",
        })

    # 2) Üretim düşük + üç zamanlı tarife → puant uyarısı
    if uretim.toplam_kwh < tuketim.toplam_kwh * 0.3 and profil.tarife_tipi == "uc_zamanli":
        uyarilar.append({
            "tur": "puant_uyari",
            "baslik": "Yarın üretim zayıf",
            "metin": "Bulutlu görünüyor; 17:00-22:00 puant diliminde büyük cihaz çalıştırmamaya çalış, "
                     "gece 22:00 sonrası en ucuz dilim.",
        })

    # 3) Batarya varsa ve yarın fazla üretim varsa şarj hatırlatması
    if profil.batarya_kwh > 0 and uretim.toplam_kwh > tuketim.toplam_kwh:
        uyarilar.append({
            "tur": "batarya",
            "baslik": "Bataryanı doldurmak için iyi gün",
            "metin": "Yarın üretim tüketimi aşıyor — bataryayı gündüz doldurup akşam puantında kullan.",
        })

    tarife = tarife_getir(yarin, profil.kullanici_tipi, profil.tarife_tipi,
                          aylik_kwh=profil.fatura_kwh_aylik)
    # 4) Saatlik mahsuplaşma bilinci (tek zamanlıda ayda bir gösterilecek ipucu)
    if profil.tarife_tipi == "tek_zamanli" and uretim.toplam_kwh > tuketim.toplam_kwh * 1.2:
        fark = tarife.saatlik_fiyat[12] - tarife.saatlik_satis_fiyat[12]
        uyarilar.append({
            "tur": "mahsup_ipucu",
            "baslik": "Fazla üretimini aynı saatte tüket",
            "metin": "Mahsuplaşma artık saatlik: şebekeye sattığın her kWh'te "
                     f"~{fark:.2f} TL kaybediyorsun. Cihazlarını güneş saatine almak birebir kazanç.",
        })

    return uyarilar
