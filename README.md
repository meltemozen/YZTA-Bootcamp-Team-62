# Takım 62 · ⚡ Voltaic

> **Çatındaki güneş, akıllıca yönetilsin.**
> Türkiye'deki çatı-GES sahibi ev ve küçük işletmeler için; üretim ve tüketimi
> tahmin edip **saatlik mahsuplaşma**, kademeli/üç zamanlı tarife kurallarına göre
> "şu cihazı şu saatte çalıştır" diye sade Türkçe konuşan, alışkanlıkları öğrenen
> ve tasarrufu **TL + CO₂** olarak kanıtlayan agent tabanlı kişisel enerji asistanı.

*(Ürün ismi değerlendirme aşamasındadır; marka çakışması nedeniyle yeni isim
adayları belirlenmiştir.)*

---

## Takım Üyeleri

Ekip 5 kişidir; herkes aktif geliştirici olarak katkı verir (bootcamp kuralı).
Scrum rolleri ekip içinde dağıtılmıştır.

| Rol | İsim | Odak |
|---|---|---|
| Product Owner / Developer | *(eklenecek)* | Ürün vizyonu + backlog + üretim modeli (VB) |
| Scrum Master / Developer | *(eklenecek)* | Süreç + iletişim + tüketim modeli & optimizasyon (VB) |
| Developer | *(eklenecek)* | Agent mimarisi + model–agent kontratı + müzakere (YZ) |
| Developer | *(eklenecek)* | Orkestrasyon + Gemini Türkçe öneri + servisler (YZ) |
| Developer | *(eklenecek)* | Hafıza + mobil/web arayüz + tarife tool'u (YZ) |

## Ürün Açıklaması

Çatısında güneş paneli olan bir ev ya da küçük işletme sahibi, ürettiği enerjiyi
ne zaman depolayacağını, hangi cihazı ne zaman çalıştıracağını bilmiyor. Üstelik
**2 Nisan 2026 mevzuat değişikliğiyle mahsuplaşma saatlik hale geldi**: üretimi
o saat içinde tüketmeyen kullanıcı, sattığı her kWh'te dağıtım bedeli ve vergiler
kadar (~%30) kaybediyor. Voltaic bu kararı kullanıcı adına veriyor:

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

## Ekran Görüntüleri

| Onboarding | Günlük Plan | Asistan |
|---|---|---|
| ![Onboarding](docs/gorseller/adim1_onboarding.png) | ![Plan](docs/gorseller/adim3_bugun.png) | ![Asistan](docs/gorseller/adim4_asistan.png) |

## Teknik Dokümantasyon

- [HANDOFF.md](HANDOFF.md) — AI agent / yeni geliştirici hızlı başlangıç (kurallar, mimari, kalınan yer, sonraki iş)
- [docs/SPRINTS.md](docs/SPRINTS.md) — sprint planı & product backlog (Trello'ya hazır kart açıklamaları)
- [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) — sistem mimarisi, ML katmanı, enerji optimizasyonu ve Türkiye uyarlaması
- [docs/research/ENERGY_OPTIMIZATION_RESEARCH.md](docs/research/ENERGY_OPTIMIZATION_RESEARCH.md) — açık kaynak enerji optimizasyonu, fiyat adapter'ı ve gerçek zamanlı yeniden planlama
- [docs/research/DEVICE_AND_EV_ASSUMPTIONS.md](docs/research/DEVICE_AND_EV_ASSUMPTIONS.md) — cihaz tüketimi ve EV şarj varsayımları
- [docs/TEKNIK.md](docs/TEKNIK.md) — mimari, kurulum, depo yapısı, kalan işler
- [docs/CONTRACT.md](docs/CONTRACT.md) — model–agent tool kontratı (kilitli, v1.2)
- [docs/METHOD.md](docs/METHOD.md) — veri doğruluğu, mevzuat kaynakları, dürüstlük ilkeleri
- [docs/DEPLOY.md](docs/DEPLOY.md) — çalıştırma, Docker, canlıya alma, demo videosu akışı

**Hızlı başlangıç:** `backend/` → `pip install -r requirements-dev.txt` → `uvicorn app.main:app` ·
`mobile/` → `npm install` → `npx expo start` (testler: `pytest tests/` — 27/27 · lint: `ruff check .`)

---

# Sprintler

> **Sprint yapısı hakkında not.** Planlanan iş takvimin önünde ilerledi: baseline
> modelli **uçtan uca çalışan ürün** ve **temiz İngilizce kod tabanı** Sprint 1
> sonunda hazır. Bu yüzden orijinal plandaki "iskelet" (S1) ve "karar zekası" (S2)
> işleri Sprint 1 altında birleştirilip **tamamlandı** olarak raporlandı; Sprint 2
> ve 3, geriye kalan **gerçek** işe (weather-aware model yükseltmesi,
> gerçek zamanlı optimizasyon, değerlendirme, canlıya alma, teslim) göre yeniden yazıldı.
> Toplam ≈ **113 SP** (S1: 48 · S2: 44 · S3: 21). Ek teknik derinlik backlog'u için
> [docs/SPRINTS.md](docs/SPRINTS.md) Trello kartlarına hazır açıklamalar içerir.

<details open>
<summary><h2>Sprint 1 — Temel, Kontrat ve Çalışan Ürün (19 Haziran – 5 Temmuz) · 48 SP · ✅ TESLİM</h2></summary>

**Sprint hedefi:** Uçtan uca çalışan ürün; model–agent kontratı kilitli; baseline
modeller + gerçek agent + mobil/web arayüz; temiz, tutarlı İngilizce kod tabanı.

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
| S1-9 | Grounding guard + agent eval suite + API sağlamlaştırma (27 test, güvenli hata cevabı, grounded fallback) | YZ | 3 | ✅ |

**Tamamlanan (kanıt):** yukarıdaki ekran görüntüleri Sprint 1 sonundaki çalışan
üründen (gerçek Open-Meteo verisi, İzmir). Mevzuat/veri doğrulaması METHOD.md'de
(2026 tarifeleri, RG 02.04.2026 saatlik mahsup, ETKB emisyon faktörü).

- **Daily Scrum:** [docs/scrum/sprint-1/daily.md](docs/scrum/sprint-1/daily.md)
- **Sprint Board:** [docs/scrum/sprint-1/board.md](docs/scrum/sprint-1/board.md) *(ekran görüntüsü hafta sonu eklenecek)*
- **Sprint Review:** [docs/scrum/sprint-1/review.md](docs/scrum/sprint-1/review.md)
- **Sprint Retrospective:** [docs/scrum/sprint-1/retrospective.md](docs/scrum/sprint-1/retrospective.md)

</details>

<details>
<summary><h2>Sprint 2 — Gerçek ML, Yerel LLM ve Optimizasyon Sağlamlaştırma (6 – 19 Temmuz) · 44 SP · 🟡 BRANCH</h2></summary>

**Hedef:** Baseline modelleri hava/veri girdili v1 artifact'lere taşı; agent'ı
Gemini/Ollama/fallback provider zinciriyle sağlamlaştır; gerçek zamanlı hava/saat
değişimlerine göre optimizer'ı uygulanabilir plan üretir hale getir.

| # | Görev | Ekip | SP | Durum |
|---|---|---|---|---|
| S2-1 | Weather-aware üretim modeli v1 + PVGIS eğitim scripti | VB | 8 | 🟡 branch |
| S2-2 | Generic smart-meter tüketim modeli v1 + shape eğitim scripti | VB | 8 | 🟡 branch |
| S2-3 | EPİAŞ şekil doğrulama + tüketim kalibrasyon raporu (METHOD §3) | VB | 5 | Planlandı |
| S2-4 | Gemini/Ollama provider zinciri + prompt iyileştirme | YZ | 5 | 🟡 branch |
| S2-5 | Chroma semantik hafıza (`memory.py` genişletme; imza sabit) | YZ | 5 | Planlandı |
| S2-6 | Cihaz kataloğu + EV şarj güç/süre metadata'sı | YZ | 3 | 🟡 branch |
| S2-7 | Expo konum izni + konuma göre hava kontrolü | YZ | 5 | 🟡 branch |
| S2-8 | Gerçek zamanlı optimizer + performans iyileştirme | YZ | 5 | 🟡 branch |

**Sprint 2 demo kriteri:** Konumdan bugünün/yarının hava tahmini alınır; v1 üretim
modeli planı besler; geçmiş saatlere öneri verilmez; EV/büyük cihazlar fiyat ve
güneş penceresine göre optimize edilir; agent bunu Türkçe ve grounded açıklar.

</details>

<details>
<summary><h2>Sprint 3 — Değerlendirme, Canlıya Alma ve Teslim (20 Temmuz – 2 Ağustos) · 21 SP · 🔜 PLANLANDI</h2></summary>

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
