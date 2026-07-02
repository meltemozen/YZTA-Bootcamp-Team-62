"""Kural tabanlı yedek planlayıcı.

Gemini anahtarı yokken veya API düştüğünde ürünün çalışmaya devam etmesini
sağlar: sabit sırayla tool çağırır, şablonla Türkçe açıklama üretir.
Bu bir "agent" DEĞİLDİR (sıra elle kuruludur) — yanıtta agent_modu='fallback'
olarak dürüstçe işaretlenir.
"""

import re

from .baglam import AracBaglami

_GEREKCE_METNI = {
    "gunes_bol": "o saatte güneş üretimi tüketimini karşılıyor",
    "puant_kacinma": "17-22 arası puant tarifesinden kaçınıyoruz",
    "gece_ucuz": "gece tarifesi en ucuz dilim",
    "mahsup_avantaji": "mahsupta satış fiyatı alıştan düşük, evde tüketmek daha kârlı",
}

_SAAT_KALIBI = re.compile(r"(\d{1,2})[:.]?(\d{2})?\s*(?:'?[dt]en|'?[dt]an)?\s*(sonra|önce|once)", re.IGNORECASE)

_TERCIH_IPUCLARI = ("evde yokum", "evde olmuyorum", "misafir", "istemiyorum",
                    "olmaz", "uyuyor", "gürültü", "gurultu", "sonra", "önce", "once")


def _tercih_mi(mesaj: str) -> bool:
    kucuk = mesaj.lower()
    return any(ipucu in kucuk for ipucu in _TERCIH_IPUCLARI)


def _yasak_saatler(mesaj: str) -> list[int]:
    """Basit kalıplar: '22den sonra olmaz' → 22..07 arası yasak."""
    eslesme = _SAAT_KALIBI.search(mesaj)
    if not eslesme:
        return []
    saat = int(eslesme.group(1)) % 24
    yon = eslesme.group(3).lower()
    if yon == "sonra":
        return [(saat + i) % 24 for i in range(0, (7 - saat) % 24 or 9)]
    return list(range(0, saat))


def _tl(alt: float, ust: float) -> str:
    """Aralığı okunur yaz; uçlar yuvarlamada eşitleşiyorsa tek değer göster."""
    if f"{alt:.0f}" == f"{ust:.0f}":
        return f"~{ust:.1f} TL"
    return f"{alt:.0f}-{ust:.0f} TL"


def cevapla(baglam: AracBaglami, mesaj: str) -> str:
    tarih = "yarin" if "yarın" in mesaj.lower() or "yarin" in mesaj.lower() else "bugun"

    yasak = []
    if mesaj and _tercih_mi(mesaj):
        baglam.hafiza_yaz(mesaj.strip())
        yasak = _yasak_saatler(mesaj)

    # Kayıtlı tercihlerden de yasak saat çıkar
    for tercih in baglam.hafiza_oku():
        yasak += _yasak_saatler(tercih["metin"])

    baglam.hava_getir(tarih)
    baglam.uretim_tahmin(tarih)
    baglam.tuketim_tahmin(tarih)
    baglam.tarife_getir(tarih)
    ozet = baglam.optimize(tarih, sorted(set(yasak)) or None)

    if not ozet["kalemler"]:
        return ("Bugün için kaydıracak esnek cihaz bulamadım. Ayarlardan çamaşır makinesi, "
                "bulaşık makinesi gibi cihazlarını ekleyebilirsin.")

    satirlar = []
    for k in ozet["kalemler"]:
        if k["tur"] == "batarya_sarj":
            satirlar.append(f"Bataryayı {k['baslangic']:02d}:00-{k['bitis']:02d}:00 arası güneşten doldur.")
        elif k["tur"] == "batarya_desarj":
            satirlar.append(f"Bataryayı {k['baslangic']:02d}:00'dan itibaren kullan "
                            f"({_tl(*k['tasarruf_tl'])}).")
        else:
            gerekce = _GEREKCE_METNI.get(k["gerekce"], "")
            satirlar.append(f"{k['ad']}: {k['baslangic']:02d}:00'da çalıştır "
                            f"({_tl(*k['tasarruf_tl'])}) — {gerekce}.")

    alt, ust = ozet["toplam_tasarruf_tl"]
    araba_km = ozet.get("cevre", {}).get("araba_km")
    cevre_eki = f" ({araba_km:.0f} km araba yolculuğuna denk)" if araba_km else ""
    genel = (f"Günün planı hazır — tahmini {_tl(alt, ust)} tasarruf, "
             f"{ozet['co2_kg']:.1f} kg CO2 önleniyor{cevre_eki}.")
    if yasak:
        genel += " Tercihlerini dikkate aldım (bazı saatler hariç tutuldu)."
    return genel + "\n\n" + "\n".join(f"• {s}" for s in satirlar)
