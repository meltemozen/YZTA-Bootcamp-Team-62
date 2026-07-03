# Voltaic — Sprint Planı & Product Backlog

> Bu belge `Voltaic_Project_Sprints.pdf`'in yerini alır. Orijinal PDF planlanan
> iş için yazılmıştı; bu belge **gerçekte yapılan işi** (Sprint 1 = teslim) ve
> **kalan gerçek işi** (Sprint 2–3) yansıtır.
>
> **Nasıl kullanılır (Trello):** her görev bir karttır. `### S1-1 …` başlığı kart
> başlığı, **Kart açıklaması** bloğu Trello açıklama alanına yapıştırılır,
> **Kabul kriteri** checklist'e, ekip etiketi (YZ/VB/Ortak) label'a, SP ise kart
> puanına konur. Sütunlar: Product Backlog → Todo → In Progress → In Review → Done.

**Bootcamp takvimi:** Sprint 1 (19 Haz–5 Tem) · Sprint 2 (6–19 Tem) · Sprint 3 (20 Tem–2 Ağu). Teslim: 2 Ağustos 2026.

**Toplam ≈ 100 SP** — Sprint 1: 45 (✅ teslim) · Sprint 2: 34 · Sprint 3: 21.

---

## Product Backlog (epic → story)

| Epic | Story (kullanıcı değeri) | Sprint |
|---|---|---|
| **A. Tahmin motoru** | Kullanıcının paneli için saatlik üretim ve hane tüketimi tahmin edilir | S1 (v0) → S2 (LightGBM v1) |
| **B. Karar & optimizasyon** | Üç zamanlı/kademeli tarife + saatlik mahsuplaşmaya göre en ucuz saat hesaplanır | S1 |
| **C. Agent katmanı** | Agent kendi kararıyla tool çağırır, itirazı hatırlar, sormadan uyarır | S1 (temel) → S2 (canlı LLM + semantik hafıza) |
| **D. Mobil + web ürün** | Kullanıcı 4 adımda kurar; plan, asistan, rapor ekranlarını Türkçe kullanır | S1 → S3 (cila) |
| **E. Kanıt & değer** | Ay sonunda gerçekleşen + kaçırılan tasarruf ve CO₂ raporlanır | S1 → S3 (değerlendirme) |
| **F. Altyapı & teslim** | Kilitli kontrat, temiz kod, CI, canlı deploy, demo | S1 → S3 |

---

## SPRINT 1 — Temel, Kontrat ve Çalışan Ürün · 19 Haz – 5 Tem

**Sprint hedefi:** Baseline modellerle uçtan uca çalışan ürün + kilitli model–agent
kontratı + temiz, tutarlı İngilizce kod tabanı.
**Hedef puan:** 45 SP · **Tamamlanan:** 45 SP.
**Puan tamamlama mantığı:** Orijinal plandaki "iskelet" (S1) ve "karar zekası" (S2)
işleri takvimin önünde bitti; ikisi birleştirilip Sprint 1 altında teslim edildi.
Puanlar Fibonacci (1/2/3/5/8); kodlama içermeyen ama kritik iş (kontrat kilidi) de puanlıdır.

### S1-1 · Repo, altyapı & İngilizce refactor  `[YZ · 5 SP · ✅]`
**Kart açıklaması:** Public GitHub repo, klasör mimarisi (backend/mobile/data/docs)
ve branch yapısı kuruldu. Sprint kapanışında tüm kod tabanı İngilizce'ye taşındı
(dosya/metot/sınıf/alan adları, tool adları, API route'ları, JSON alanları); mobil
arayüz metinleri Türkçe bırakıldı. `.gitattributes`, `.dockerignore`, CI eklendi.
**Kabul kriteri:** Repo public · testler yeşil · repoda artık Türkçe kod tanımlayıcı yok · CI geçiyor.
**Kod:** tüm depo · `.github/workflows/ci.yml`

### S1-2 · Model–Agent tool kontratını KİLİTLE  `[Ortak · 3 SP · ✅]`
**Kart açıklaması:** Agent'ın modelleri nasıl çağıracağı, girdi/çıktı JSON şemaları
Pydantic ile tanımlandı ve kilitlendi. İki ekip (YZ/VB) bu kontrat üzerinden paralel
çalışır; değişiklik ancak ortak kararla yapılır.
**Kabul kriteri:** 6 tool imzası + tüm şemalar `schemas.py`'de · CONTRACT.md yayınlandı · `model_version` alanı v1 geçişine hazır.
**Kod:** `backend/app/schemas.py` · `docs/CONTRACT.md`

### S1-3 · Veri boru hattı (PVGIS + Open-Meteo)  `[VB · 5 SP · ✅]`
**Kart açıklaması:** Python scriptiyle PVGIS (SARAH3, saatlik ışınım + PV üretim)
ve Open-Meteo (canlı/geçmiş hava) verileri Türkiye koordinatları için çekilip
temizlendi. Open-Meteo aynı zamanda agent'ın canlı tool'u.
**Kabul kriteri:** `pvgis_fetch.py` CSV üretiyor · `get_weather` canlı veriyi dönüyor · ağ yoksa cache/sentetik fallback.
**Kod:** `data/scripts/pvgis_fetch.py` · `backend/app/tools/weather.py`

### S1-4 · Backend: FastAPI + Docker + SQLite  `[YZ · 3 SP · ✅]`
**Kart açıklaması:** FastAPI uygulaması (mobil ekranlarla 1:1 uçlar), Dockerfile +
docker-compose, SQLite kalıcılık (kullanıcı, tercih/hafıza, plan geçmişi, geri bildirim).
**Kabul kriteri:** `/api/health` 200 · Docker imajı ayağa kalkıyor · DB volume ile kalıcı.
**Kod:** `backend/app/main.py` · `backend/app/db.py` · `backend/Dockerfile`

### S1-5 · 6 tool + optimizasyon motoru  `[VB+YZ · 8 SP · ✅]`
**Kart açıklaması:** get_weather, forecast_production (v0 fiziksel), forecast_consumption
(fatura kalibrasyonu), get_tariff (kademeli + üç zamanlı + **saatlik mahsuplaşma**),
optimize (deterministik cihaz/batarya planı), read/write_memory. Optimizasyon "neden
13:00?" sorusunu açıklanabilir şekilde cevaplar.
**Kabul kriteri:** Cihaz güneş fazlası saatine yerleşir · üç zamanlıda puanta asla girmez · batarya gündüz şarj/pahalı saat deşarj · testlerle doğrulandı.
**Kod:** `backend/app/tools/*` · `backend/tests/test_core.py`

### S1-6 · Gemini agent + fallback + müzakere döngüsü  `[YZ · 8 SP · ✅]`
**Kart açıklaması:** Gemini function-calling döngüsü: agent hangi tool'u ne zaman
çağıracağına kendi karar verir; kullanıcı itirazını (ör. "salı öğlen evde yokum")
hafızaya yazıp planı yeniden kurar. Anahtar yoksa kural-tabanlı fallback devrede
(ürün asla durmaz, `agent_mode='fallback'` işaretlenir).
**Kabul kriteri:** itiraz → write_memory → optimize zinciri çalışıyor · fallback modda uçtan uca yanıt · çağrılan tool zinciri şeffaf dönüyor.
**Kod:** `backend/app/agent/*`

### S1-7 · Mobil + web uygulaması (Expo)  `[YZ · 8 SP · ✅]`
**Kart açıklaması:** Tek Expo kod tabanı → Android/iOS + web. 5 ekran: Onboarding
(4 adım), Bugün (plan + 24s grafik), Asistan (agent sohbeti), Rapor, Ayarlar.
Marka kimliği (koyu tema, SVG logo, Space Grotesk + Inter). Arayüz Türkçe.
**Kabul kriteri:** onboarding → plan → asistan akışı çalışıyor · grafik dokunmatik inceleme · web build alınabiliyor.
**Kod:** `mobile/*`

### S1-8 · Proaktif uyarı + karşı-olgusal rapor + CO₂ + testler  `[Ortak · 5 SP · ✅]`
**Kart açıklaması:** Sorulmadan tetiklenen proaktif uyarı ajanı ("yarın güneş bol");
ay sonu raporu (gerçekleşen + karşı-olgusal "kaçırılan fırsat"); CO₂/çevre eşdeğerleri
(araba km, ağaç). 14 birim/entegrasyon testi + mevzuat/veri doğrulaması.
**Kabul kriteri:** rapor uçları çalışıyor · 14/14 test yeşil · mevzuat kaynakları METHOD.md'de.
**Kod:** `backend/app/services/*` · `backend/tests/test_api.py`

**Scrum kanıtları:** [daily](scrum/sprint-1/daily.md) · [board](scrum/sprint-1/board.md) · [review](scrum/sprint-1/review.md) · [retrospective](scrum/sprint-1/retrospective.md)

---

## SPRINT 2 — Gerçek ML & Agent Sağlamlaştırma · 6 – 19 Tem

**Sprint hedefi:** Baseline modelleri gerçek makine öğrenmesiyle değiştir; agent'ı
canlı Gemini anahtarıyla sağlamlaştır. **Kontrat sabit — yalnız tool gövdeleri değişir.**
**Hedef puan:** 34 SP.
**Puan tamamlama mantığı:** En yüksek jüri ağırlığı "AI/ML modeli" kaleminde; bu
sprint puanın çoğu (16 SP) iki gerçek LightGBM modeline ayrıldı.

### S2-1 · LightGBM üretim modeli v1  `[VB · 8 SP]`
**Kart açıklaması:** PVGIS + Open-Meteo geçmiş verisiyle saatlik PV üretimi tahmin
eden LightGBM modelini eğit. `forecast_production` gövdesini değiştir, imzayı ve
`ProductionForecast` şemasını KORU; `model_version`'ı `v1-lightgbm` yap.
**Kabul kriteri:** son yıl hold-out'ta v0 fiziksel baseline'ı nMAE'de geçiyor · imza değişmedi · testler yeşil.
**Kod:** `backend/app/tools/production.py` (gövde)

### S2-2 · LightGBM tüketim modeli v1  `[VB · 8 SP]`
**Kart açıklaması:** Hane/KOBİ saatlik talebini tahmin eden LightGBM modelini eğit;
`forecast_consumption` gövdesini değiştir, şema sabit.
**Kabul kriteri:** baseline profili geçiyor · fatura kalibrasyonu korunuyor · imza sabit.
**Kod:** `backend/app/tools/consumption.py` (gövde)

### S2-3 · EPİAŞ şekil doğrulama + kalibrasyon raporu  `[VB · 5 SP]`
**Kart açıklaması:** Tüketim profili şeklini EPİAŞ bölgesel/toplam tüketim eğrisiyle
karşılaştır; korelasyonu ve kalibrasyon yöntemini METHOD.md §3'te raporla.
**Kabul kriteri:** EPİAŞ ile şekil korelasyonu belgelendi · sapma noktaları not edildi.
**Kod:** `docs/METHOD.md` · analiz notebook/script

### S2-4 · Gemini canlı anahtar + prompt iyileştirme  `[YZ · 5 SP]`
**Kart açıklaması:** Gerçek `GEMINI_API_KEY` ile uçtan uca agent testi; sistem
promptu ve tool açıklamalarını gerçek çıktılarla iyileştir (Türkçe kısalık, gerekçe,
tasarruf aralığı kuralları). Hata/timeout durumlarında fallback'e düşüşü doğrula.
**Kabul kriteri:** canlı modda 5+ senaryo (plan, itiraz, tercih hatırlama) doğru · fallback düşüşü sorunsuz.
**Kod:** `backend/app/agent/orchestrator.py`

### S2-5 · Chroma semantik hafıza  `[YZ · 5 SP]`
**Kart açıklaması:** SQLite hafızanın üstüne Chroma/FAISS ile semantik arama ekle
(`search_preferences(query)`); benzer geçmiş tercihleri agent bağlamına getir.
Tool imzaları değişmez, yalnız `memory.py` genişler.
**Kabul kriteri:** semantik geri getirme çalışıyor · mevcut read/write_memory imzası bozulmadı · anahtarsız ortamda SQLite'a düşüyor.
**Kod:** `backend/app/tools/memory.py`

### S2-6 · Cihaz kataloğu + EV şarj ince ayarı  `[YZ · 3 SP]`
**Kart açıklaması:** Cihaz referans tablosunu genişlet; EV şarjı gibi büyük esnek
yükler için pencere/güç parametrelerini gerçekçileştir ve optimizasyonu test et.
**Kabul kriteri:** EV senaryosu güneş penceresine doğru yerleşiyor · katalog ≥10 cihaz.
**Kod:** `backend/app/data/devices.json` · `backend/app/tools/optimize.py`

**Sprint 2 demo kriteri:** "Çamaşırı 13:00'te at" önerisi v1 LightGBM üretim tahminiyle
üretiliyor; kullanıcı itirazıyla değişiyor; hafıza tercihi hatırlıyor.

---

## SPRINT 3 — Değerlendirme, Canlıya Alma ve Teslim · 20 Tem – 2 Ağu

**Sprint hedefi:** Modelleri değerlendir, ürünü canlıya al, teslim paketini hazırla.
**Hedef puan:** 21 SP.
**Puan tamamlama mantığı:** Yeni teknik risk alınmaz; var olan sağlamlaştırılır ve
"canlıya alınabilirlik" + teslim kalemleri (jüri ekstra puanı) tamamlanır.

### S3-1 · Model doğruluk raporu  `[VB · 5 SP]`
**Kart açıklaması:** Üretim + tüketim modellerinin test verisindeki hata paylarını
(nMAE, MAE) hesapla; v0 baseline vs v1 karşılaştırmasını grafiklerle raporla.
**Kabul kriteri:** hold-out metrikleri tabloda · v0/v1 kıyası · METHOD.md'ye eklendi.
**Kod:** `docs/METHOD.md` · değerlendirme scripti

### S3-2 · Canlıya alma (backend + APK)  `[Ortak · 5 SP]`
**Kart açıklaması:** Backend'i Railway/Cloud Run'a Docker ile deploy et (env: GEMINI_API_KEY,
VOLTAIC_CORS_ORIGINS, DB volume). EAS ile Android APK üret; `app.json` extra.apiUrl'ı
canlı URL'e bağla.
**Kabul kriteri:** canlı `/api/health` erişilebilir · APK kuruluyor ve canlı backend'e bağlanıyor.
**Kod:** `mobile/app.json` · deploy ayarları

### S3-3 · EPDK tarife + mahsup son teyidi  `[Ortak · 2 SP]`
**Kart açıklaması:** Teslim öncesi EPDK güncel tarife tablosu ve mahsup satış oranını
resmi kaynaktan teyit et; `config.py`'yi güncelle, tarihi METHOD.md'ye işle.
**Kabul kriteri:** fiyatlar/oranlar güncel kaynağa dayanıyor · tarih belgelendi.
**Kod:** `backend/app/config.py` · `docs/METHOD.md`

### S3-4 · Demo videosu + README finalize + teslim formu  `[Ortak · 5 SP]`
**Kart açıklaması:** 3 dakikalık senaryolu demo videosu (DEPLOY.md §6 akışı) çek,
YouTube'a yükle; README'yi finalize et (ekran görüntüleri, canlı link); teslim
formunu eksiksiz doldur.
**Kabul kriteri:** video ≤3 dk · README tam · form gönderildi.
**Kod:** `README.md` · video

### S3-5 · Erişilebilirlik + son cila  `[YZ · 4 SP]`
**Kart açıklaması:** UI hata/boş durum ekranları, yükleniyor göstergeleri, dokunma
hedefleri, kontrast; küçük performans ve tutarlılık düzeltmeleri.
**Kabul kriteri:** ağ hatasında anlamlı ekran · boş durumlar ele alınmış · temel erişilebilirlik geçişi.
**Kod:** `mobile/src/*`

**Teslim (2 Ağustos):** public GitHub repo · canlı URL (varsa) · 3 dk YouTube videosu · eksiksiz teslim formu.

---

## Yol haritası (v2 — sprint dışı, vizyon)

Sprinte eklenmeyen ama sunum "ürün buraya gidiyor" slaytı için: multi-agent yapı
(uzman tahmin/optimizasyon/müzakere ajanları), NILM otomatik cihaz tanıma, mahalle
mikro-paylaşım (P2P) simülasyonu ve **gerçek güneş paneli / akıllı sayaç donanım
entegrasyonu** (inverter API'leri, Modbus/MQTT, ev enerji yönetim sistemleri).
Donanım entegrasyonu için araştırma notu: [HANDOFF.md](../HANDOFF.md) → "Gelecek araştırma".
