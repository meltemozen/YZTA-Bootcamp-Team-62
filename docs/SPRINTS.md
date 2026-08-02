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
**Kabul kriteri:** `pvgis_fetch.py` CSV üretiyor · `get_weather` eksiksiz canlı veriyi dönüyor · servis hatası kullanıcıya açıkça iletiliyor.
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

### S1-6 · Gemini agent + müzakere döngüsü  `[YZ · 8 SP · ✅]`
**Kart açıklaması:** Gemini function-calling döngüsü: agent hangi tool'u ne zaman
çağıracağına kendi karar verir; kullanıcı itirazını (ör. "salı öğlen evde yokum")
hafızaya yazıp planı yeniden kurar. Gemini kullanılamıyorsa hazırlanmış veya uydurma
yanıt dönmek yerine asistan isteği açık bir servis hatasıyla sonlanır.
**Kabul kriteri:** itiraz → write_memory → optimize zinciri çalışıyor · tool çıktıları dışında sayı üretilmiyor · model hatası kullanıcıya güvenli iletiliyor.
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
TL/CO₂ rakamı, tool'ların ürettiği plana bağlı değilse yakalanır. Senaryo-tabanlı
agent testleri (`test_agent.py`) provider zorunluluğunu, tercih kalıcılığını ve
grounding kurallarını doğrular. API'ye global hata yakalayıcı + istek
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

### S2-1 · Weather-aware üretim modeli v1  `[VB · 8 SP · ✅]`
**Kart açıklaması:** PVGIS/Open-Meteo saatlik verisiyle eğitilebilir, runtime'da
Open-Meteo'nun anlık/gelecek kısa dalga ışınımı, sıcaklık ve bulut verisini kullanan
üretim modeli. `forecast_production` gövdesi zorunlu LightGBM artifact'ini okur;
eksik model deployment hatasıdır. Eğitim scripti PVGIS CSV'den artifact üretir.
**Kabul kriteri:** `model_version="v1-weather-regressor"` · güneşli/bulutlu gün farkı testli · imza değişmedi · testler yeşil.
**Kod:** `backend/app/tools/production.py` · `backend/app/models/production_v1.json` · `data/scripts/train_production_model_lgbm.py`

### S2-2 · Generic smart-meter tüketim modeli v1  `[VB · 8 SP · ✅]`
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

### S2-4 · Gemini function-calling + prompt iyileştirme  `[YZ · 5 SP · ✅]`
**Kart açıklaması:** Gerçek `GEMINI_API_KEY` ile uçtan uca agent; her LLM cevabı
grounding guard'dan geçer. Hata veya timeout durumunda hazırlanmış bir yanıt üretilmez.
Sistem promptu ve tool açıklamaları gerçek çıktılarla iyileştirilir.
**Kabul kriteri:** Gemini tool çağrıları çalışıyor · grounding ihlali engelleniyor · anahtarsız ortam güvenli 503 döndürüyor.
**Kod:** `backend/app/agent/orchestrator.py` · `backend/app/config.py`

### S2-5 · Chroma semantik hafıza  `[YZ · 5 SP]`
**Kart açıklaması:** SQLite hafızanın üstüne Chroma/FAISS ile semantik arama ekle
(`search_preferences(query)`); benzer geçmiş tercihleri agent bağlamına getir.
Tool imzaları değişmez, yalnız `memory.py` genişler.
**Kabul kriteri:** semantik geri getirme çalışıyor · mevcut read/write_memory imzası bozulmadı · anahtarsız ortamda SQLite'a düşüyor.
**Kod:** `backend/app/tools/memory.py`

### S2-6 · Cihaz kataloğu + EV şarj senaryosu (güç-bilinçli, kesintili)  `[YZ · 3 SP · ✅]`
**Kart açıklaması:** Cihaz kataloğu güç/süre/kategori/kaynak metadata'sıyla 12
cihaza çıkarıldı. Optimizer artık `power_kw`'yi FİZİKSEL kısıt olarak kullanıyor:
bir çalıştırma `kwh/power_kw` saatten hızlı bitemez (kullanıcı 22 kWh EV şarjına
1 saat yazsa bile plan 3 saate yayılır). EV şarjı ve pompalar
`flexibility="interruptible"` — şarj DURAKLAYABİLİR: saatler marjinal maliyete
göre tek tek seçilir, bloke saatlerin etrafından dolaşır ve güneş penceresine
yapışır; bölünmüş plan mobile "(1. bölüm) / (2. bölüm)" kartları olarak iner.
Çamaşır/bulaşık gibi cihazlar kesintisiz blok kalır (davranış değişmedi).
**Kabul kriteri:** EV bloke öğle saatinin etrafından dolaşıp güneş penceresinde kalıyor · üç zamanlıda EV asla 17-22 puanta girmiyor · `kwh>power_kw×süre` fizibilite düzeltmesi çalışıyor · katalog ≥10 cihaz ve tüm satırlar `Device` şemasını geçiyor · 5 yeni test.
**Kod:** `backend/app/data/devices.json` · `backend/app/tools/optimize.py` · `backend/tests/test_core.py`

### S2-7 · Expo konum izni + konuma göre hava kontrolü  `[YZ · 5 SP · ✅]`
**Kart açıklaması:** Onboarding'de kullanıcıdan konum izni iste; izin verilirse gerçek
lat/lon ile Open-Meteo hava/ışınım kontrolü yap, tahmini günlük üretimi göster ve
profili bu koordinatla kaydet. Plan endpoint'i bu konumun bugün/yarın hava tahminiyle
optimizasyon üretir.
**Kabul kriteri:** kullanıcı izin verirse gerçek koordinat kaydedilir · izin yoksa şehir seçimi çalışır · `/api/weather-check` üretim modeliyle hava özeti döner · mobile dependency uyumlu.
**Kod:** `mobile/src/screens/Onboarding.js` · `mobile/src/api.js` · `mobile/app.config.js` · `backend/app/main.py`

### S2-8 · Gerçek zamanlı optimizer + performans iyileştirme  `[YZ · 5 SP · ✅]`
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
Canlı Gemini modunda bu yakalama sadece hataya dönüşmekle kalmasın; agent'a
"şu sayılar araç çıktısında yok" geri bildirimi verilip cevabı yeniden ürettiren
repair loop eklensin. İkinci deneme de başarısızsa güvenli servis hatası döner.
**Kabul kriteri:** sahte 999 TL senaryosu kullanıcıya hiç sızmıyor · bir başarılı repair testi · başarısız repair güvenli hata veriyor.
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
**Kart açıklaması:** İstek loglarının üstüne `request_id`, provider, tool sayısı,
hata nedeni ve süre metriklerini ekle. Demo sırasında "agent ne yaptı?" sorusuna
loglardan cevap verilebilir.
**Kabul kriteri:** her assistant çağrısında request_id · provider/hata nedeni loglanır · stack trace kullanıcıya sızmaz.
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

**Sprint hedefi:** Ürünü production build'e hazırla: hesap, veri şeffaflığı,
kullanıcı tarifesi/cihaz ayarları, deploy hattı ve güven veren hata durumları.
**Hedef puan:** 27 SP.
**Puan tamamlama mantığı:** Ayrı rapor/demo kartları yerine doğrudan production
çıktısı veren işler puanlanır.

### S3-1 · Kullanıcı hesabı ve profil yönetimi  `[YZ · 8 SP · ✅]`
**Kart açıklaması:** E-posta/şifre ile register-login-logout, JWT access/refresh,
kullanıcıya özel profil ve cross-user erişim koruması.
**Kabul kriteri:** login/register çalışıyor · token refresh var · başka kullanıcının
plan/profil verisine erişilemiyor · profil güncellemesi planı yeniliyor.
**Kod:** `backend/app/auth.py` · `backend/app/main.py` · `mobile/src/AuthContext.js`

### S3-2 · Production veri gerçekliği ve model şeffaflığı  `[YZ+VB · 5 SP · ✅]`
**Kart açıklaması:** Mock/default görünen alanları temizle veya açık etiketle; hava
kaynağı, model versiyonları, optimizer versiyonu ve simülasyon uyarılarını API/UI'da göster.
**Kabul kriteri:** live/cached/synthetic görünür · model manifest endpoint'i var ·
"sayaçtan ölçülmüş tasarruf" iddiası yok.
**Kod:** `backend/app/model_manifest.py` · `mobile/src/components/States.js`

### S3-3 · Tarife, cihaz ve optimizasyon ayarları  `[YZ+VB · 5 SP · ✅]`
**Kart açıklaması:** Sabit tarife iddiasını kullanıcı override'ı ile yumuşat; cihaz
tüketim/süre/güç değerleri düzenlenebilir olsun; EV, batarya ve çoklu cihaz testlerini sertleştir.
**Kabul kriteri:** kullanıcı fiyatı öncelikli · cihaz editörü var · EV/batarya
constraint testleri geçiyor.
**Kod:** `backend/app/tools/tariff.py` · `mobile/src/components/ProfileEditors.js`

### S3-4 · Production deployment ve build stabilitesi  `[Ortak · 5 SP · ✅]`
**Kart açıklaması:** Expo Web ve FastAPI'yi tek production image içinde Railway'e
deploy et; kalıcı volume, custom domain, EAS build profilleri, env tabanlı
API URL ve smoke test ekle.
**Kabul kriteri:** `/api/health` canlı · Railway volume bağlı · custom domain
doğrulanmış · Expo Doctor temiz · Android APK canlı backend'e bağlanıyor.
**Kod:** `backend/Dockerfile` · `railway.json` · `mobile/app.config.js` · `mobile/eas.json`

### S3-5 · Arayüz, hata durumları ve kullanıcı güveni  `[YZ · 4 SP · ✅]`
**Kart açıklaması:** Loading/empty/error ekranları, anlık işlem geri bildirimi,
erişilebilir dokunma hedefleri ve kullanıcıya yönelik temiz metinler ekle; geliştirme
ayarlarını ve model/altyapı ayrıntılarını son kullanıcı ekranlarından kaldır.
**Kabul kriteri:** ağ ve doğrulama hataları anlamlı gösterilir · konum seçimi geri
bildirim verir · API adresi sabit production config'den gelir · teknik geliştirme
metinleri kullanıcıya gösterilmez · temel erişilebilirlik geçişi.
**Kod:** `mobile/src/components/States.js` · `mobile/src/screens/*`

**Teslim (2 Ağustos):** public GitHub repo · canlı web/API domaini · Android EAS APK
· smoke test sonucu · güncel README. iOS TestFlight yüklemesi Apple hesabı etkileşimli
kimlik doğrulamasıyla release işlemi olarak yürütülür.

---

## Yol haritası (v2 — sprint dışı, vizyon)

Sprinte eklenmeyen ama sunum "ürün buraya gidiyor" slaytı için: multi-agent yapı
(uzman tahmin/optimizasyon/müzakere ajanları), NILM otomatik cihaz tanıma, mahalle
mikro-paylaşım (P2P) simülasyonu ve **gerçek güneş paneli / akıllı sayaç donanım
entegrasyonu** (inverter API'leri, Modbus/MQTT, ev enerji yönetim sistemleri).
Donanım entegrasyonu için inverter API, Modbus/MQTT güvenliği ve kullanıcı onayı ayrı
bir teknik keşif çalışması olarak yürütülecektir.
