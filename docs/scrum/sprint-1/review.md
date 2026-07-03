# Sprint 1 — Sprint Review

**Tarih:** 5 Temmuz 2026 · **Sprint hedefi:** Uçtan uca çalışan ürün + kilitli
kontrat + temiz İngilizce kod tabanı. **Sonuç: hedef aşıldı (45/45 SP).**

## Teslim edilen artırım (increment)

Çalışan, uçtan uca ürün:

1. **Kayıt/onboarding** → 4 adımda profil (ev/işyeri, il, panel, fatura, cihazlar).
2. **Günlük plan** → cihaz/batarya için saat saat öneri, gerekçesi + tasarruf
   aralığı (TL) + CO₂; 24 saatlik üretim/tüketim grafiği.
3. **Asistan (agent)** → serbest Türkçe sohbet; Gemini kendi kararıyla tool çağırır,
   itirazı hafızaya yazıp planı yeniden kurar; çağrılan tool zinciri şeffaf gösterilir.
   Anahtar yoksa kural-tabanlı fallback devrede (ürün asla durmaz).
4. **Proaktif uyarı** → sorulmadan "yarın güneş bol, çamaşırı öğlene planla".
5. **Ay sonu raporu** → gerçekleşen tasarruf + karşı-olgusal "kaçırılan fırsat" + CO₂.

## Demo kriteri

Orijinal S1 demo kriteri ("yarınki üretim tahmini agent üzerinden dönüyor") **karşılandı
ve aşıldı**: agent yalnız üretim değil, çoklu tool orkestrasyonuyla tam bir gerekçeli
plan üretiyor ve itiraza göre yeniden planlıyor.

## Değerlendirme kriterleriyle eşleşme (öz-değerlendirme)

- **Yapay Zeka öğeleri (35):** iki ML tool katmanı + gerçek agent (tool-use, hafıza,
  orkestrasyon) — organik, sonradan yapıştırma değil.
- **Fonksiyonel yeterlilik (15):** çalışan uçtan uca ürün (mobil + web + API).
- **Temiz mimari (ekstra 15):** kilitli kontrat, tek noktadan sabitler (`config.py`),
  İngilizce tutarlı kod tabanı, 14 test.
- **Canlıya alınabilirlik (ekstra 10):** Docker hazır; canlı URL Sprint 3'te.

## Kapsam dışı bırakılan / ertelenen

- Gerçek LightGBM modelleri (şu an v0 baseline) → **Sprint 2**.
- Chroma semantik hafıza (şu an SQLite, imza genişletmeye hazır) → **Sprint 2**.
- Canlı URL + APK + demo videosu → **Sprint 3**.
