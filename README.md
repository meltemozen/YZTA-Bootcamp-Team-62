# Takım 62 · ⚡ WATTRA

> **Çatındaki güneş, akıllıca yönetilsin.**
> Türkiye'deki çatı-GES sahibi ev ve küçük işletmeler için; üretim ve tüketimi
> tahmin edip **saatlik mahsuplaşma**, kademeli/üç zamanlı tarife kurallarına göre
> "şu cihazı şu saatte çalıştır" diye sade Türkçe konuşan, alışkanlıkları öğrenen
> ve tasarrufu **TL + CO₂** olarak kanıtlayan agent tabanlı kişisel enerji asistanı.

*(Ürün ismi değerlendirme aşamasındadır; marka çakışması nedeniyle yeni isim
adayları belirlenmiştir.)*

---

## Takım Üyeleri

Ekip 5 kişidir; herkes aktif geliştirici olarak katkı verir.
Scrum rolleri ekip içinde dağıtılmıştır.

| Rol | İsim | Odak |
|---|---|---|
| Product Owner / Developer | Elanur DEMİR | Ürün vizyonu + backlog + üretim modeli (YZ) |
| Scrum Master / Developer | Meltem ÖZEN | Süreç + iletişim + tüketim modeli & optimizasyon (VB) |
| Developer | Berkan ÖKSÜZ | Agent mimarisi + model–agent kontratı + müzakere (VB) |
| Developer | İshak Bedir YORGANCI | Orkestrasyon + Gemini Türkçe öneri + servisler (YZ) |
| Developer | Kübra GEZİCİ | Hafıza + mobil/web arayüz + tarife tool'u (YZ) |

## Ürün Açıklaması

Çatısında güneş paneli olan bir ev ya da küçük işletme sahibi, ürettiği enerjiyi
ne zaman depolayacağını, hangi cihazı ne zaman çalıştıracağını bilmiyor. Üstelik
**2 Nisan 2026 mevzuat değişikliğiyle mahsuplaşma saatlik hale geldi**: üretimi
o saat içinde tüketmeyen kullanıcı, sattığı her kWh'te dağıtım bedeli ve vergiler
kadar (~%30) kaybediyor. Wattra bu kararı kullanıcı adına veriyor:

**"Çamaşırı yarın 13:00'te at — ~9-14 TL ve 2.9 kg CO₂ (17 km araba yoluna denk) tasarruf, çünkü öğlen üretimin tüketimini karşılıyor."**

İki makine öğrenmesi modeli (üretim + tüketim tahmini) agent'ın çağırdığı birer
tool olarak çalışır; Gemini tabanlı agent hangi tool'u ne zaman çağıracağına kendi
karar verir, kullanıcının itirazını hafızasına yazar ve planı yeniden kurar.

## Ürün Özellikleri

- 📱 **Mobil uygulama + web sitesi** (tek Expo/React Native kod tabanı)
- 🗓 **Günlük plan:** cihaz ve batarya için saat saat öneri, gerekçesiyle
- 🤖 **Gerçek agent:** Gemini function-calling; tool zinciri kullanıcıya şeffaf gösterilir
- 🧠 **Öğrenen hafıza:** "Salı öğlen evde yokum" → kaydeder, planı değiştirir
- 💰 **Gerçek Türkiye ekonomisi:** kademeli tarife (240 kWh eşiği), üç zamanlı
  dilimler, saatlik mahsuplaşma, 10 kW mesken sınırı uyarısı — hepsi kaynaklı
- 🌱 **Çevresel etki:** ETKB emisyon faktörüyle CO₂ + "araba km / ağaç" eşdeğerleri
- 📊 **Ay sonu raporu:** gerçekleşen tasarruf + karşı-olgusal "kaçırılan fırsat"
- 🔔 **Proaktif uyarı:** "Yarın güneş bol, çamaşırı öğlene planla" — sorulmadan
- 🌐 Türkçe, sıfır teknik bilgi varsayımı, 4 adımda kurulum (saatlik sayaç verisi İSTEMEZ)

## Hedef Kitle

Türkiye'de çatı-GES sahibi (veya kurmayı değerlendiren) **ev kullanıcıları** ve
**küçük işletmeler** (dükkan, atölye, tarımsal sulama) — teknik bilgisi olmayan,
faturasını düşürmek ve güneşinden en yüksek faydayı almak isteyen herkes.


## Product Backlog
[Miro Backlog](https://miro.com/app/board/uXjVHA5ySr8=/?share_link_id=612821934232)

---

# Sprintler

<details open>
<summary><h2>Sprint 1 (19 Haziran – 5 Temmuz) · 48 SP</h2></summary>

**Sprint Notları:** Bu sprint'te hem projenin temeli atıldı hem de tüm ekibin uyumlu çalışabilmesi için gerekli düzenlemeler yapıldı. Takım rolleri belirlendi. Projede yapılacak tasklar belirlendi ve product backlog olarak boarda eklendi. Repo, GitHub & proje altyapısı düzenlendi. Model-agent kontratı oluşturuldu ve tüm ekibin uyumlu çalışabilmesi için gerekli düzenlemeler yapıldı.

**Tamamlanan Puan:** Sprint 1 için 48 puanlık iş yapılacağı belirlenmiştir ve 48 puanlık iş tamamlanmıştır.

**Tahmin Mantığı:** Yapılacak taskların her biri zorluk, öncelik ve yapılma süresine bağlı olarak puanlandırılmıştır. Tüm sprintler için toplam puan 103'tür. Sprint 1 için 48 puan planlanmış ve 48 puan tamamlanmıştır. Sprint 1'de daha çok projenin iskeletinin oluşturulması, temel fonksiyonların yazılması ve agent'ın test edilmesi hedeflenmiştir. Bu nedenle diğer sprintlere göre daha çok puan verilmiştir.


**Daily Scrum:** Whatsapp üzerinden toplantı saatleri kararlaştırılıp Meet veya Slack üzerinden toplantılar gerçekleştirilmiştir. Bu kısa toplantılarla ekip üyeleri tamamladıkları işleri, yapacakları task'ları ve karşılaştıkları engelleri paylaşarak ilerleme kaydedilmiştir. 

![Sprint 1 Huddle](docs/gorseller/sprint1_huddle.jpeg)

![Daily Scrum](docs/gorseller/sprint1_meet.png)


**Sprint Board Ekran Görüntüleri**
![Sprint Board Updates](docs/gorseller/sprint1_scrumboard.png)

![Sprint Board Updates](docs/gorseller/sprint1_scrumboard2.png)

**Sprint 1 Burndown Chart**

![Sprint 1 Burndown Chart](docs/gorseller/sprint1_burndownChart.png)

![Sprint 1 System Architecture](docs/gorseller/sprint1_systemarchitecture.png)

## Ürün Ekran Görüntüleri

| Onboarding | Günlük Plan | Asistan |
|---|---|---|
| ![Onboarding](docs/gorseller/adim1_onboarding.png) | ![Plan](docs/gorseller/adim3_bugun.png) | ![Asistan](docs/gorseller/adim4_asistan.png) |


**Sprint Review:** Hangi veri setlerinin kullanılacağına karar verilip PVGIS ve Open-Meteo API entegrasyonları yapılarak veri çekme scriptleri yazıldı. FastAPI ile backend iskeleti oluşturuldu ve Expo kullanılarak mobil/web uygulamasının temel sayfaları (onboarding, plan, asistan vb.) kodlandı. Ayrıca agent yapısı için 6 farklı tool geliştirilerek optimizasyon motoru devreye alındı ve kapsamlı testlerle (uçtan uca doğrulama) sistem sağlamlaştırıldı.

**Sprint Retrospective:** Diğer 2 sprintte daha verimli çalışılacağına ve daha planlı toplantı yapılması gerektiğine karar verildi.

| # | Görev | Ekip | SP | Durum |
|---|---|---|---|---|
| S1-1 | Repo, GitHub & proje altyapısı + **İngilizce refactor** (dosya/metot/alan adları) + klasör mimarisi | YZ | 5 | ✅ |
| S1-2 | Model–Agent tool kontratını tasarla ve **KİLİTLE** (Pydantic `schemas.py` + CONTRACT.md) | Ortak | 3 | ✅ |
| S1-3 | Veri boru hattı: PVGIS + Open-Meteo çekme/temizleme scriptleri | VB | 5 | ✅ |
| S1-4 | Backend: FastAPI + Docker iskeleti + SQLite kalıcılık | YZ | 3 | ✅ |
| S1-5 | 6 agent tool'u + **optimizasyon motoru** (weather, production v0, consumption v0, tariff+saatlik mahsup, optimize, memory) | VB+YZ | 8 | ✅ |
| S1-6 | Gemini function-calling agent + kural-tabanlı fallback + **müzakere döngüsü** (itiraz → hafıza → yeniden planla) | YZ | 8 | ✅ |
| S1-7 | Mobil + web uygulaması (Expo tek kod tabanı: onboarding, plan, asistan, rapor, ayarlar + grafik + marka) | YZ | 8 | ✅ |
| S1-8 | Proaktif uyarılar + karşı-olgusal ay sonu raporu + CO₂/çevre katmanı + **14 test** & uçtan uca doğrulama | Ortak | 5 | ✅ |
| S1-9 | Grounding guard + agent eval suite + API sağlamlaştırma (20 test, güvenli hata cevabı, grounded fallback) | YZ | 3 | ✅ |

</details>

<details>
<summary><h2>Sprint 2 (6 – 19 Temmuz) · 34 SP</h2></summary>

**Sprint hedefi:** Tahmin motorunu v1 model artifact'leriyle güçlendirmek ve planı
kullanıcının gerçek konumu + anlık/gelecek hava tahminiyle üretmek.

**Bu branch'te yapılan işler:**

**Sprint 2 Scrum Board**

![Sprint 2 Scrum Board](docs/gorseller/sprint2_scrumboard.png)

| Kart | Ekip | SP | Durum | Kod karşılığı |
|---|---|---:|---|---|
| S2-1 Weather-aware üretim modeli v1 | VB | 8 | Branch'te | `backend/app/tools/production.py`, `backend/app/models/production_v1.json`, `data/scripts/train_production_model.py` |
| S2-2 Generic smart-meter tüketim modeli v1 | VB | 8 | Branch'te | `backend/app/tools/consumption.py`, `backend/app/models/consumption_v1.json`, `data/scripts/train_consumption_model.py` |
| S2-4 Gemini/Ollama provider zinciri | YZ | 5 | Branch'te | `backend/app/agent/orchestrator.py`, `backend/app/agent/local_llm.py`, `backend/app/config.py` |
| S2-6 Cihaz kataloğu + EV şarj metadata'sı | YZ | 3 | Branch'te | `backend/app/data/devices.json`, `backend/app/tools/optimize.py`, `docs/research/DEVICE_AND_EV_ASSUMPTIONS.md` |
| S2-7 Expo konum izni + hava kontrolü | YZ | 5 | Branch'te | `mobile/src/screens/Onboarding.js`, `mobile/src/api.js`, `backend/app/main.py` |
| S2-8 Gerçek zamanlı optimizer + performans | YZ | 5 | Branch'te | `backend/app/tools/weather.py`, `backend/app/tools/optimize.py`, `backend/app/tools/tariff.py`, `docs/research/ENERGY_OPTIMIZATION_RESEARCH.md` |

**Notlar**

- Çalışma branch'i: `ml/s2-weather-local-llm`.
- Model yaklaşımı LightGBM'e kilitlenmedi. Öncelik doğru runtime girdileri:
  konum, bugün/yarın hava tahmini, ışınım, sıcaklık, bulut ve fatura kalibrasyonu.
- Üretim modeli PVGIS CSV ile yeniden eğitilebilir. Tüketim modeli açık smart-meter
  CSV'lerinden saatlik şekil çıkarıp kullanıcının faturasıyla ölçekler.
- Plan her çağrıda yeniden optimize edilir; bugünün geçmiş saatleri cihaz ve batarya
  dispatch için otomatik bloklanır.

</details>

<details>
<summary><h2>Sprint 3 (20 Temmuz – 2 Ağustos) · 21 SP </h2></summary>

**Hedef:** Modelleri değerlendir, ürünü canlıya al, teslim paketini hazırla.

| # | Görev | Ekip | SP |
|---|---|---|---|
| S3-1 | Model doğruluk raporu (nMAE, hold-out; v0 baseline vs v1) | VB | 5 |
| S3-2 | Canlıya alma: Railway/Cloud Run backend + EAS ile Android APK | Ortak | 5 |
| S3-3 | EPDK güncel tarife + mahsup bedeli son teyidi (`config.py`) | Ortak | 2 |
| S3-4 | 3 dk demo videosu + README finalize + teslim formu | Ortak | 5 |
| S3-5 | Erişilebilirlik + son cila (UI durumları, hata ekranları) | YZ | 4 |

**Teslim (2 Ağustos):** public GitHub repo, canlı URL (varsa), 3 dk YouTube videosu,
eksiksiz teslim formu.

</details>

---

*Google Yapay Zeka ve Teknoloji Akademisi Bootcamp 2026 · Yapay Zeka & Veri Bilimi kategorisi*
