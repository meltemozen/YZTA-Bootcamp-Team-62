# Model–Agent Tool Kontratı (KİLİTLİ)

> Bu kontrat iki ekibin (Yapay Zeka + Veri Bilimi) buluşma noktasıdır.
> Kod karşılığı: `backend/app/schemas.py`. Değişiklik ancak iki ekibin ortak
> kararıyla ve bu dosya + şema birlikte güncellenerek yapılır.
>
> **Kilitlenme tarihi:** 2 Temmuz 2026 (Sprint 1)
> **v1.1 (3 Temmuz 2026):** Saatlik mahsuplaşma mevzuatı (RG 02.04.2026) gereği
> `TarifeBilgisi`ye `saatlik_satis_fiyat[24]` eklendi; kademeli tarife için
> `tarife_getir` opsiyonel `aylik_kwh` parametresi aldı. Geriye uyumlu.

## Tool listesi

Agent bu tool'ları **kendi kararıyla, kendi sırasıyla** çağırır — elle pipeline yoktur.
(Gemini function-calling döngüsü: `backend/app/agent/orkestrator.py`)

| Tool | Girdi | Çıktı | Sahibi | Durum |
|---|---|---|---|---|
| `hava_getir(konum, tarih)` | koordinat, gün | saatlik ışınım/sıcaklık/bulutluluk (`HavaDurumu`) | YZ | ✅ canlı (Open-Meteo) |
| `uretim_tahmin(hava, panel_kw)` | hava + panel kapasitesi | saatlik kWh üretim (`UretimTahmini`) | **VB** | ✅ v0-fiziksel — VB, v1-LightGBM ile değiştirir |
| `tuketim_tahmin(hane_profili, tarih)` | profil + gün | saatlik kWh baz talep (`TuketimTahmini`) | **VB** | ✅ v0-profil — VB, v1 ile değiştirir |
| `tarife_getir(tarih, tip)` | gün, kullanıcı/tarife tipi | saatlik fiyat + **mahsup satış fiyatı** (`TarifeBilgisi`) | YZ | ✅ EPDK sabit tablo |
| `optimize(üretim, tüketim, tarife, profil, yasak_saatler)` | hepsi | cihaz/batarya planı (`GunlukPlan`) | DS+YZ | ✅ deterministik motor |
| `hafiza_oku(kullanici_id)` / `hafiza_yaz(kullanici_id, metin)` | kullanıcı id | tercih + geçmiş | YZ | ✅ SQLite (Chroma genişletilebilir) |

## Orijinal dokümandan farklar (gerekçeli)

1. **`tarife_getir` artık `mahsup_satis_fiyati` da döner.** Mahsuplaşma "projenin
   farklılaştırıcı çekirdeği" olduğu halde orijinal kontratta yoktu. Satış fiyatının
   alış fiyatından düşük olması, optimizasyonun "öz tüketim > satış" önceliğinin
   ekonomik temelidir.
2. **`tuketim_tahmin` profil içinde `fatura_kwh_aylik` alır.** Türkiye'de kullanıcı
   saatlik tüketimini bilemez; fatura kalibrasyonu tek gerçekçi girdidir (bkz. METHOD.md).
3. **`optimize` `yasak_saatler` parametresi aldı.** Hafızadaki tercihlerin
   ("öğlen evde yokum") plana bağlanma noktası budur.

## VB ekibi için değiştirme sözleşmesi

`uretim_tahmin` ve `tuketim_tahmin` fonksiyonlarının **imzası ve çıktı şeması
sabittir**. LightGBM modelleri hazır olduğunda yalnızca fonksiyon gövdesi değişir,
`model_surumu` alanı `v1-lightgbm` yapılır. Agent, API ve mobil uygulama hiçbir
değişiklik gerektirmez — kontratın amacı tam olarak budur.

## Veri tipleri

Tüm saatlik diziler **24 elemanlı** olup yerel saat 00:00–23:00'ı temsil eder.
Ayrıntılı alan tanımları: [`backend/app/schemas.py`](../backend/app/schemas.py)
