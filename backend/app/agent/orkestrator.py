"""Gemini function-calling orkestratörü.

"Gerçek agent" tanımının kod karşılığı: Gemini hangi tool'u ne zaman
çağıracağına KENDİ karar verir (elle pipeline yok), hafızayı okur,
kullanıcı itirazında tercihi hafızaya yazıp yeniden planlar.

GEMINI_API_KEY yoksa veya çağrı hata verirse fallback.plan_uret devreye
girer — ürün asla cevapsız kalmaz, yanıtta agent_modu='fallback' görünür.
"""

import logging

from .. import config
from ..schemas import AsistanYanit, HaneProfili
from . import fallback
from .baglam import AracBaglami

log = logging.getLogger(__name__)

SISTEM_TALIMATI = """Sen Voltaic'sin: Türkiye'deki çatı güneş paneli (çatı-GES) sahibi ev ve
küçük işletmelere enerji kararı veren kişisel asistan. Sade, samimi Türkçe konuşursun;
teknik jargon kullanmazsın.

GÖREVİN: Kullanıcının hedefine ulaşmak için elindeki araçları KENDİ kararınla, gereken
sırayla çağır; sonuçları birleştirip gerekçeli tek bir öneri metni üret.

KURALLAR:
1. Plan istenince önce hafiza_oku ile tercihleri kontrol et; plana aykırı tercih varsa
   optimize'ı yasak_saatler ile çağır (örn. "22'den sonra çamaşır istemiyor" → 22,23,0..7).
2. Tasarrufu HER ZAMAN aralık olarak söyle ("yaklaşık 12-18 TL"); kesin rakam verme,
   çünkü tüketim tahmini fatura kalibrasyonuna dayanır.
3. Önerinin NEDENİNİ tek cümleyle açıkla: güneş bol / puant pahalı / gece ucuz /
   saatlik mahsuplaşmada satış alıştan ~%30 ucuz olduğu için üretimi o saat içinde
   evde tüketmek kârlı.
4. Kullanıcı bir alışkanlık, kısıt veya itiraz söylerse (örn. "salı öğlen evde yokum")
   ÖNCE hafiza_yaz ile kaydet, SONRA optimize'ı yeni kısıtla tekrar çağırıp planı güncelle.
5. Saat dilimleri (üç zamanlı tarife): gündüz 06-17, puant 17-22 (en pahalı), gece 22-06 (en ucuz).
   Mevzuat bilgin: mahsuplaşma 1 Mayıs 2026'dan beri SAATLİKTİR; mesken tek zamanlı
   tarife kademelidir (240 kWh/ay üstü daha pahalı); mesken çatı GES sınırı 10 kW.
6. TL tasarrufun yanında ÇEVRESEL faydayı da an: optimize çıktısındaki co2_kg ve
   cevre.araba_km değerlerini kullan ("2.9 kg CO₂ — 17 km araba yolculuğuna denk").
7. Cevabın kısa olsun: en fazla 4-5 cümle + gerekiyorsa saat listesi. Emoji en fazla bir tane.
8. Bilmediğin şeyi uydurma; araç çıktısında olmayan sayı söyleme."""

ARAC_TANIMLARI = [
    {"name": "hava_getir",
     "description": "Bir günün saatlik hava ve güneş ışınımı özetini getirir (Open-Meteo canlı).",
     "parameters": {"type": "object", "properties": {
         "tarih": {"type": "string", "description": "'bugun', 'yarin' veya YYYY-MM-DD"}}}},
    {"name": "uretim_tahmin",
     "description": "Kullanıcının paneli için bir günün saatlik güneş üretim tahminini hesaplar.",
     "parameters": {"type": "object", "properties": {
         "tarih": {"type": "string", "description": "'bugun', 'yarin' veya YYYY-MM-DD"}}}},
    {"name": "tuketim_tahmin",
     "description": "Hanenin/işyerinin baz elektrik tüketim tahminini getirir.",
     "parameters": {"type": "object", "properties": {
         "tarih": {"type": "string"}}}},
    {"name": "tarife_getir",
     "description": "Elektrik tarifesini ve mahsuplaşma (şebekeye satış) fiyatını getirir.",
     "parameters": {"type": "object", "properties": {
         "tarih": {"type": "string"}}}},
    {"name": "optimize",
     "description": "Cihaz ve batarya için en ucuz günlük planı kurar. Kullanıcının istemediği "
                    "saatler varsa yasak_saatler ver.",
     "parameters": {"type": "object", "properties": {
         "tarih": {"type": "string"},
         "yasak_saatler": {"type": "array", "items": {"type": "integer"},
                           "description": "Cihaz çalıştırılmayacak saatler (0-23)"}}}},
    {"name": "hafiza_oku",
     "description": "Kullanıcının kayıtlı tercih ve alışkanlıklarını getirir.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "hafiza_yaz",
     "description": "Kullanıcının söylediği kalıcı tercih/alışkanlığı hafızaya yazar.",
     "parameters": {"type": "object", "properties": {
         "metin": {"type": "string"}}, "required": ["metin"]}},
]

MAKS_ADIM = 8


def _gemini_dongusu(baglam: AracBaglami, mesaj: str) -> str:
    from google import genai
    from google.genai import types

    istemci = genai.Client(api_key=config.GEMINI_API_KEY)
    uret_ayar = types.GenerateContentConfig(
        system_instruction=SISTEM_TALIMATI,
        tools=[types.Tool(function_declarations=ARAC_TANIMLARI)],
        temperature=0.3,
    )
    icerik = [types.Content(role="user", parts=[types.Part(text=mesaj)])]

    for _ in range(MAKS_ADIM):
        yanit = istemci.models.generate_content(
            model=config.GEMINI_MODEL, contents=icerik, config=uret_ayar)
        aday = yanit.candidates[0].content
        cagrilar = [p.function_call for p in (aday.parts or []) if p.function_call]
        if not cagrilar:
            return yanit.text or ""

        icerik.append(aday)
        sonuc_parcalari = []
        for fc in cagrilar:
            arac = getattr(baglam, fc.name, None)
            try:
                sonuc = arac(**dict(fc.args)) if arac else {"hata": f"bilinmeyen araç {fc.name}"}
            except Exception as hata:  # aracın hatası agent'a bildirilir, döngü kırılmaz
                log.exception("Araç hatası: %s", fc.name)
                sonuc = {"hata": str(hata)}
            sonuc_parcalari.append(types.Part.from_function_response(
                name=fc.name, response={"sonuc": sonuc}))
        icerik.append(types.Content(role="tool", parts=sonuc_parcalari))

    return "Planı kurdum ama açıklamayı kısa kesmek zorunda kaldım — plan kartlarına bakabilirsin."


def asistan_cevapla(kullanici_id: int, profil: HaneProfili, mesaj: str) -> AsistanYanit:
    baglam = AracBaglami(kullanici_id, profil)

    if config.GEMINI_API_KEY:
        try:
            metin = _gemini_dongusu(baglam, mesaj)
            return AsistanYanit(yanit=metin, plan=baglam.son_plan,
                                agent_modu="gemini", arac_cagrilari=baglam.cagrilar)
        except Exception:
            log.exception("Gemini orkestrasyonu düştü, fallback'e geçiliyor")

    metin = fallback.cevapla(baglam, mesaj)
    return AsistanYanit(yanit=metin, plan=baglam.son_plan,
                        agent_modu="fallback", arac_cagrilari=baglam.cagrilar)
