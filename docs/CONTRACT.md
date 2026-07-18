# Model–Agent Tool Kontratı (KİLİTLİ)

> Bu kontrat iki ekibin (Yapay Zeka + Veri Bilimi) buluşma noktasıdır.
> Kod karşılığı: `backend/app/schemas.py`. Değişiklik ancak iki ekibin ortak
> kararıyla ve bu dosya + şema birlikte güncellenerek yapılır.
>
> **Kilitlenme tarihi:** 2 Temmuz 2026 (Sprint 1)
> **v1.1 (3 Temmuz 2026):** Saatlik mahsuplaşma mevzuatı (RG 02.04.2026) gereği
> `Tariff`e `hourly_sell_price[24]` eklendi; kademeli tarife için `get_tariff`
> opsiyonel `monthly_kwh` parametresi aldı. Geriye uyumlu.
> **v1.2 (3 Temmuz 2026):** Kod tabanı İngilizce'ye taşındı (dosya/metot/alan
> adları). Tool imzaları ve JSON alanları İngilizce; anlam ve şekil AYNI.
> Kullanıcıya görünen mobil metinler Türkçe kaldı.
> **v1.3 (9 Temmuz 2026, S2-5):** Yeni EKLEME tool: `search_preferences(user_id,
> query, top_k=5)` — Chroma + Gemini embedding ile anlamca benzer tercihleri
> getirir; katman yoksa SQLite kelime eşleşmesine düşer. `read_memory` /
> `write_memory` imzaları DEĞİŞMEDİ; mevcut şemalara dokunulmadı. Geriye uyumlu.
> **v1.4 (9 Temmuz 2026, S2-6):** Davranış eki, şema DEĞİŞMEDİ: `optimize`
> artık `Device.power_kw`'yi fiziksel kısıt sayar (efektif süre ≥ kwh/power_kw)
> ve `Device.flexibility="interruptible"` cihazları (EV şarjı, pompa) kesintili
> yerleştirebilir. Bölünmüş yerleşim, mevcut `PlanItem` şemasıyla **bitişik
> segment başına bir kalem** olarak döner (ad soneki "(N. bölüm)"). Geriye uyumlu.

## Tool listesi

Agent bu tool'ları **kendi kararıyla, kendi sırasıyla** çağırır — elle pipeline yoktur.
(Gemini function-calling döngüsü: `backend/app/agent/orchestrator.py`)

| Tool | Girdi | Çıktı | Sahibi | Durum |
|---|---|---|---|---|
| `get_weather(lat, lon, date)` | koordinat, gün | saatlik ışınım/sıcaklık/bulutluluk (`Weather`) | YZ | ✅ canlı (Open-Meteo) |
| `forecast_production(weather, panel_kw)` | hava + panel kapasitesi | saatlik kWh üretim (`ProductionForecast`) | **VB** | ✅ v0-physical — VB, v1-lightgbm ile değiştirir |
| `forecast_consumption(profile, date)` | profil + gün | saatlik kWh baz talep (`ConsumptionForecast`) | **VB** | ✅ v0-profile — VB, v1 ile değiştirir |
| `get_tariff(date, user_type, tariff_type, monthly_kwh)` | gün, kullanıcı/tarife tipi | saatlik fiyat + **mahsup satış fiyatı** (`Tariff`) | YZ | ✅ EPDK sabit tablo |
| `optimize(production, consumption, tariff, profile, blocked_hours)` | hepsi | cihaz/batarya planı (`DailyPlan`) | DS+YZ | ✅ deterministik motor |
| `read_memory(user_id)` / `write_memory(user_id, text)` | kullanıcı id | tercih + geçmiş | YZ | ✅ SQLite (+ Chroma'ya çift yazım) |
| `search_preferences(user_id, query, top_k)` | kullanıcı id + serbest metin | anlamca benzer tercihler (`text/source/date/similarity`) | YZ | ✅ Chroma + Gemini embedding; katman yoksa kelime eşleşmesi |

## Enum değerleri (İngilizce, v1.2)

- `user_type`: `home` | `business`
- `tariff_type`: `single` | `three_zone`
- `PlanItem.type`: `device` | `battery_charge` | `battery_discharge`
- `reason_code`: `solar_surplus` | `avoid_peak` | `cheap_night` | `netmeter_edge`
- `band`: `day` | `peak` | `night` | `flat`
- `agent_mode`: `gemini` | `fallback`

## Orijinal dokümandan farklar (gerekçeli)

1. **`get_tariff` artık `avg_sell_price` + `hourly_sell_price` de döner.**
   Mahsuplaşma "projenin farklılaştırıcı çekirdeği" olduğu halde orijinal
   kontratta yoktu. Satış fiyatının alış fiyatından düşük olması, optimizasyonun
   "öz tüketim > satış" önceliğinin ekonomik temelidir.
2. **`forecast_consumption` profil içinde `monthly_bill_kwh` alır.** Türkiye'de
   kullanıcı saatlik tüketimini bilemez; fatura kalibrasyonu tek gerçekçi
   girdidir (bkz. METHOD.md).
3. **`optimize` `blocked_hours` parametresi aldı.** Hafızadaki tercihlerin
   ("öğlen evde yokum") plana bağlanma noktası budur.

## VB ekibi için değiştirme sözleşmesi

`forecast_production` ve `forecast_consumption` fonksiyonlarının **imzası ve
çıktı şeması sabittir**. LightGBM modelleri hazır olduğunda yalnızca fonksiyon
gövdesi değişir, `model_version` alanı `v1-lightgbm` yapılır. Agent, API ve
mobil uygulama hiçbir değişiklik gerektirmez — kontratın amacı tam olarak budur.

## Veri tipleri

Tüm saatlik diziler **24 elemanlı** olup yerel saat 00:00–23:00'ı temsil eder.
Ayrıntılı alan tanımları: [`backend/app/schemas.py`](../backend/app/schemas.py)
