# Wattra — Sprint Planı & Product Backlog

> Bu belge `Wattra_Project_Sprints.pdf`'in yerini alır. Orijinal PDF planlanan
> iş için yazılmıştı; bu belge **gerçekte yapılan işi** (Sprint 1 = teslim) ve
> **kalan gerçek işi** (Sprint 2–3) yansıtır.
>
> **Nasıl kullanılır (Trello):** her görev bir karttır. `### S1-1 …` başlığı kart
> başlığı, **Kart açıklaması** bloğu Trello açıklama alanına yapıştırılır,
> **Kabul kriteri** checklist'e, ekip etiketi (YZ/VB/Ortak) label'a, SP ise kart
> puanına konur. Sütunlar: Product Backlog → Todo → In Progress → In Review → Done.

**Bootcamp takvimi:** Sprint 1 (19 Haz–5 Tem) · Sprint 2 (6–19 Tem) · Sprint 3 (20 Tem–2 Ağu). Teslim: 2 Ağustos 2026.

**Toplam ≈ 113 SP** — Sprint 1: 48 (✅ teslim) · Sprint 2: 44 · Sprint 3: 21.
Ayrıca aşağıda **Teknik Derinlik Backlog'u (YZ ağırlıklı)** var: Sprint 2'yi
zorlaştırmak / projeyi production'a taşımak için seçilebilecek 8 derin görev.

---

## Product Backlog (epic → story)

| Epic | Story (kullanıcı değeri) | Sprint |
|---|---|---|
| **A. Tahmin motoru** | Kullanıcının paneli için saatlik üretim ve hane tüketimi tahmin edilir | S1 (v0) → S2 (weather-aware v1) |
| **B. Karar & optimizasyon** | Üç zamanlı/kademeli tarife + saatlik mahsuplaşmaya göre en ucuz saat hesaplanır | S1 |
| **C. Agent katmanı** | Agent kendi kararıyla tool çağırır, itirazı hatırlar, sormadan uyarır | S1 (temel) → S2 (canlı LLM + semantik hafıza) |
| **D. Mobil + web ürün** | Kullanıcı 4 adımda kurar; plan, asistan, rapor ekranlarını Türkçe kullanır | S1 → S3 (cila) |
| **E. Kanıt & değer** | Ay sonunda gerçekleşen + kaçırılan tasarruf ve CO₂ raporlanır | S1 → S3 (değerlendirme) |
| **F. Altyapı & teslim** | Kilitli kontrat, temiz kod, CI, canlı deploy, demo | S1 → S3 |

---

## SPRINT 1 — Temel, Kontrat ve Çalışan Ürün · 19 Haz – 5 Tem

**Sprint hedefi:** Baseline modellerle uçtan uca çalışan ürün + kilitli model–agent
kontratı + temiz, tutarlı İngilizce kod tabanı.
**Hedef puan:** 48 SP · **Tamamlanan:** 48 SP.
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

### S1-9 · Grounding guard + agent eval suite + API sağlamlaştırma  `[YZ · 3 SP · ✅]`
**Kart açıklaması:** Agent'ın "sayı uydurmama" dürüstlük kuralını **kod düzeyinde**
zorunlu kılan grounding guard (`grounding.py`): agent'ın Türkçe cevabındaki her
TL/CO₂ rakamı, tool'ların ürettiği plana bağlı değilse yakalanır. Fallback agent
için senaryo-tabanlı 6 eval testi (`test_agent.py`): doğru tool orkestrasyonu,
kısıt uyumu, tercih kalıcılığı, grounding ve canlı LLM grounding fallback'i. API'ye global hata yakalayıcı + istek
loglama; Gemini tool argümanları defensive temizlenir (bilinmeyen arg atılır,
`blocked_hours` 0–23'e clamp).
**Kabul kriteri:** 27/27 test yeşil · uydurma rakam (999 TL) testte yakalanıyor · ruff temiz · beklenmeyen hatada stack sızmıyor.
**Kod:** `backend/app/agent/grounding.py` · `backend/tests/test_agent.py` · `backend/app/main.py` · `backend/app/agent/orchestrator.py`

**Scrum kanıtları:** [daily](scrum/sprint-1/daily.md) · [board](scrum/sprint-1/board.md) · [review](scrum/sprint-1/review.md) · [retrospective](scrum/sprint-1/retrospective.md)

---

## SPRINT 2 — Gerçek ML & Agent Sağlamlaştırma · 6 – 19 Tem

**Sprint hedefi:** Baseline modelleri gerçek makine öğrenmesiyle değiştir; agent'ı
canlı Gemini anahtarıyla sağlamlaştır. **Kontrat sabit — yalnız tool gövdeleri değişir.**
**Hedef puan:** 44 SP.
**Puan tamamlama mantığı:** En yüksek jüri ağırlığı "AI/ML modeli" kaleminde; bu
sprint puanın çoğu (16 SP) iki gerçek v1 tahmin modeline ayrıldı.

### S2-1 · Weather-aware üretim modeli v1  `[VB · 8 SP · 🟡 branch]`
**Kart açıklaması:** PVGIS/Open-Meteo saatlik verisiyle eğitilebilir, runtime'da
Open-Meteo'nun anlık/gelecek kısa dalga ışınımı, sıcaklık ve bulut verisini kullanan
üretim modeli. `forecast_production` gövdesi v1 model artifact'ini okur; model
yoksa fiziksel fallback devreye girer. Eğitim scripti PVGIS CSV'den artifact üretir.
**Kabul kriteri:** `model_version="v1-weather-regressor"` · güneşli/bulutlu gün farkı testli · imza değişmedi · testler yeşil.
**Kod:** `backend/app/tools/production.py` · `backend/app/models/production_v1.json` · `data/scripts/train_production_model.py`

### S2-2 · Generic smart-meter tüketim modeli v1  `[VB · 8 SP · 🟡 branch]`
**Kart açıklaması:** Hane/KOBİ saatlik talebini açık smart-meter verisinden çıkarılabilen
24 saatlik yük şekli + kullanıcının aylık faturasıyla kalibre eden v1 model. Türkiye'ye
özel sayaç verisi gerekmez; generic şekil kullanıcı faturasıyla ölçeklenir.
**Kabul kriteri:** `model_version="v1-generic-load-shape"` · fatura kalibrasyonu korunuyor · hafta sonu/mevsim etkisi var · imza sabit.
**Kod:** `backend/app/tools/consumption.py` · `backend/app/models/consumption_v1.json` · `data/scripts/train_consumption_model.py`

### S2-3 · EPİAŞ şekil doğrulama + kalibrasyon raporu  `[VB · 5 SP]`
**Kart açıklaması:** Tüketim profili şeklini EPİAŞ bölgesel/toplam tüketim eğrisiyle
karşılaştır; korelasyonu ve kalibrasyon yöntemini METHOD.md §3'te raporla.
**Kabul kriteri:** EPİAŞ ile şekil korelasyonu belgelendi · sapma noktaları not edildi.
**Kod:** `docs/METHOD.md` · analiz notebook/script

### S2-4 · Gemini/Ollama provider zinciri + prompt iyileştirme  `[YZ · 5 SP · 🟡 branch]`
**Kart açıklaması:** Gerçek `GEMINI_API_KEY` ile uçtan uca agent testi; anahtar yoksa
opsiyonel `OLLAMA_ENABLED=1` ile yerel Ollama tool-calling provider'ı çalıştır. Her
LLM cevabı grounding guard'dan geçer; hata/timeout durumlarında deterministik fallback
devreye girer. Sistem promptu ve tool açıklamaları gerçek çıktılarla iyileştirilir.
**Kabul kriteri:** Gemini/Ollama/fallback provider sırası çalışıyor · local LLM testleri daemon gerektirmeden mock'lanıyor · grounding ihlalinde fallback.
**Kod:** `backend/app/agent/orchestrator.py` · `backend/app/agent/local_llm.py` · `backend/app/config.py`

### S2-5 · Chroma semantik hafıza  `[YZ · 5 SP]`
**Kart açıklaması:** SQLite hafızanın üstüne Chroma/FAISS ile semantik arama ekle
(`search_preferences(query)`); benzer geçmiş tercihleri agent bağlamına getir.
Tool imzaları değişmez, yalnız `memory.py` genişler.
**Kabul kriteri:** semantik geri getirme çalışıyor · mevcut read/write_memory imzası bozulmadı · anahtarsız ortamda SQLite'a düşüyor.
**Kod:** `backend/app/tools/memory.py`

### S2-6 · Cihaz kataloğu + EV şarj ince ayarı  `[YZ · 3 SP · 🟡 branch]`
**Kart açıklaması:** Cihaz referans tablosunu güç/süre/kategori/kaynak metadata'sı
ile genişlet; EV Level 2 şarjı gibi büyük esnek yükler için gerçekçi pencere/güç
parametreleri ekle ve optimizasyonu test et.
**Kabul kriteri:** EV senaryosu bloklu saatlere girmiyor · katalog ≥10 cihaz · cihazlarda `power_kw/category/source` metadata var.
**Kod:** `backend/app/data/devices.json` · `backend/app/tools/optimize.py`

### S2-7 · Expo konum izni + konuma göre hava kontrolü  `[YZ · 5 SP · 🟡 branch]`
**Kart açıklaması:** Onboarding'de kullanıcıdan konum izni iste; izin verilirse gerçek
lat/lon ile Open-Meteo hava/ışınım kontrolü yap, tahmini günlük üretimi göster ve
profili bu koordinatla kaydet. Plan endpoint'i bu konumun bugün/yarın hava tahminiyle
optimizasyon üretir.
**Kabul kriteri:** kullanıcı izin verirse gerçek koordinat kaydedilir · izin yoksa şehir seçimi çalışır · `/api/weather-check` üretim modeliyle hava özeti döner · mobile dependency uyumlu.
**Kod:** `mobile/src/screens/Onboarding.js` · `mobile/src/api.js` · `mobile/app.json` · `backend/app/main.py`

### S2-8 · Gerçek zamanlı optimizer + performans iyileştirme  `[YZ · 5 SP · 🟡 branch]`
**Kart açıklaması:** Planı her çağrıda güncel hava/saat/kısıtlarla yeniden hesapla:
Open-Meteo current koşullarını bugünün ilgili saatine işle, geçmiş saatleri cihaz ve
batarya dispatch için otomatik blokla, cihaz yerleşimini greedy + coordinate descent
ile iyileştir, model artifact okumalarını cache'le ve Türkiye/dinamik fiyat adapter
mimarisini araştırma raporlarıyla belgele.
**Kabul kriteri:** bugün geçmiş saate plan yok · batarya geçmiş saatte şarj/deşarj etmiyor · optimizer metadata'sı (`device_optimizer`, `cost_evaluations`) dönüyor · 27/27 test yeşil.
**Kod:** `backend/app/tools/weather.py` · `backend/app/tools/optimize.py` · `backend/app/tools/tariff.py` · `docs/research/*`

**Sprint 2 demo kriteri:** "Çamaşırı 13:00'te at" önerisi v1 weather-aware üretim tahminiyle
üretiliyor; kullanıcı itirazıyla değişiyor; hafıza tercihi hatırlıyor.

---

## Teknik Derinlik Backlog'u — Sprint 2/3 için seçilebilir kartlar

Bu bölüm Trello'da `Product Backlog` altında tutulabilir. Amaç kart sayısını
şişirmek değil; jürinin AI/ML, sağlam mimari ve canlıya alınabilirlik kriterlerinde
gerçek kanıt üreten işleri görünür yapmak. Sprint kapasitesine göre 2-4 kart seçmek
yeterli; kalanlar v2 yol haritası olarak durabilir.

### TDB-1 · Agent grounding repair loop  `[YZ · 5 SP]`
**Kart açıklaması:** Grounding guard bugün uydurulmuş TL/CO₂ sayılarını yakalıyor.
Canlı Gemini modunda bu yakalama sadece fallback'e düşmekle kalmasın; agent'a
"şu sayılar araç çıktısında yok" geri bildirimi verilip cevabı yeniden ürettiren
repair loop eklensin. İkinci deneme de başarısızsa deterministik fallback döner.
**Kabul kriteri:** sahte 999 TL senaryosu kullanıcıya hiç sızmıyor · bir başarılı repair testi · başarısız repair'de fallback.
**Kod:** `backend/app/agent/orchestrator.py` · `backend/tests/test_agent.py`

### TDB-2 · Golden conversation eval set  `[YZ · 5 SP]`
**Kart açıklaması:** 15-20 sabit Türkçe konuşma senaryosu oluştur: plan isteme,
itiraz, çelişkili tercih, batarya, üç zamanlı tarife, cihaz yok, bilinmeyen şehir,
gereksiz kesin rakam talebi. Her senaryo agent mode, tool zinciri, grounded numbers
ve plan kısıtlarına göre otomatik puanlanır.
**Kabul kriteri:** `pytest` içinde deterministic eval set · en az 15 senaryo · CI'da koşar.
**Kod:** `backend/tests/test_agent_eval.py`

### TDB-3 · Permissioned automation / Home Assistant simülasyonu  `[YZ · 8 SP]`
**Kart açıklaması:** Gerçek donanım gerektirmeden "akıllı priz/EV şarj" entegrasyonunu
güvenli simüle et: agent yalnızca kullanıcının açık onayıyla `schedule_device_action`
tool'unu çağırır; önce plan önerir, sonra onay mesajı gelirse aksiyonu kayıt altına alır.
Bu, projeyi karar destekten güvenli otonom enerji asistanı vizyonuna taşır.
**Kabul kriteri:** onaysız aksiyon yok · onaylı aksiyon DB'ye kaydediliyor · mobile'da "planlandı" durumu görünüyor.
**Kod:** `backend/app/tools/automation.py` · `backend/app/db.py` · `mobile/src/screens/Assistant.js`

### TDB-4 · Model artifact registry + versioned metrics  `[VB+YZ · 5 SP]`
**Kart açıklaması:** v0/v1 model dosyaları ve metriklerini tek manifestte tut:
model_version, eğitim veri aralığı, nMAE/MAE, kaynak, oluşturma tarihi. API health
ve METHOD.md bu manifestten model sürümünü gösterir.
**Kabul kriteri:** manifest var · health endpoint model sürüm özetini döner · METHOD.md metrik tablosu manifestle tutarlı.
**Kod:** `backend/app/models/manifest.json` · `backend/app/main.py` · `docs/METHOD.md`

### TDB-5 · Tarife/mevzuat regression fixture  `[Ortak · 3 SP]`
**Kart açıklaması:** EPDK tarife ve saatlik mahsup varsayımlarını fixture/test haline getir.
Fiyat sabitleri değişince optimizer ekonomisi bozulursa test yakalar.
**Kabul kriteri:** tek/üç zamanlı fiyat fixture'ı · satış fiyatı alıştan düşük invariant'ı · örnek plan regression testi.
**Kod:** `backend/tests/fixtures/tariff_2026.json` · `backend/tests/test_tariff_regression.py`

### TDB-6 · Observability-ready API  `[YZ · 3 SP]`
**Kart açıklaması:** İstek loglarının üstüne `request_id`, `agent_mode`, tool sayısı,
fallback nedeni ve süre metriklerini ekle. Demo sırasında "agent ne yaptı?" sorusuna
loglardan cevap verilebilir.
**Kabul kriteri:** her assistant çağrısında request_id · agent_mode/fallback_reason loglanır · stack trace kullanıcıya sızmaz.
**Kod:** `backend/app/main.py` · `backend/app/agent/orchestrator.py`

### TDB-7 · Mobile offline/error states polish  `[YZ · 5 SP]`
**Kart açıklaması:** Backend kapalı, ağ yavaş, boş cihaz listesi, plan yok, rapor verisi
yok durumları için gerçek kullanıcı akışları tasarla. Kullanıcı teknik hata yerine
ne yapabileceğini görür.
**Kabul kriteri:** 5 hata/boş durum ekranı · tekrar dene aksiyonu · Turkish UI korunur · web/mobile görsel kontrol.
**Kod:** `mobile/src/*`

### TDB-8 · Demo data seed + one-command showcase  `[Ortak · 3 SP]`
**Kart açıklaması:** Jüri demosu için İzmir ev + küçük işletme + bataryalı senaryo
seed verisi ve tek komutla ayağa kalkan showcase akışı hazırla.
**Kabul kriteri:** seed scripti · README demo komutu · aynı senaryo her makinede tekrar üretilebilir.
**Kod:** `backend/app/demo_seed.py` · `README.md`

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
WATTRA_CORS_ORIGINS, DB volume). EAS ile Android APK üret; `app.json` extra.apiUrl'ı
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
