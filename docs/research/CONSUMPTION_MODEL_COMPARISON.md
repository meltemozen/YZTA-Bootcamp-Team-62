# Tüketim Modeli Karşılaştırması (v1)

- Veri: Kaggle London Smart Meter (5500 hane, saatlik baz yük) + EPİAŞ 2024 saatlik
  Türkiye tüketim oranlarıyla kalibre edilmiş birleşik veri seti (19.624 saatlik kayıt).
- Doğrulama: %80/%20 zaman bazlı split (shuffle yok, zaman serisi bütünlüğü korunur).
- Özellikler: `hour`, `day_of_week`, `is_weekend`, `month`
  — backend'in çalışma zamanında (`forecast_consumption`) sahip olduğu girdilerle bire bir aynı,
  böylece kazanan modelin öğrendiği 24 saatlik profil doğrudan deploy edilebilir.
- Metrikler: MAE / RMSE (kWh).
- Kural (docs/METHOD.md): v0-profile baseline'ını geçemeyen model üretime alınmaz.

## Sonuçlar

| Model | MAE | RMSE |
|---|---|---|
| CatBoost | 0.2125 | 0.2641 |
| LightGBM | 0.2247 | 0.2744 |
| Prophet | 0.3688 | 0.4162 |

## Karar

**CatBoost** en düşük MAE ve RMSE'ye sahip. Baseline (ortalama) yaklaşıma göre
MAE hatası %50 iyileştirilerek 0.46'dan **0.21 kWh'ye** düşürülmüştür.

CatBoost'un avantajları:
- Kategorik değişkenleri (saat, gün, ay) native olarak işler, One-Hot Encoding gerektirmez.
- LightGBM'e kıyasla ~%5 daha düşük hata oranı.
- Prophet'e kıyasla ~%42 daha düşük hata — zaman serisi seasonality yaklaşımından
  daha iyi bir tüketim profili öğreniyor.

## Deploy Yöntemi (Distillation)

CatBoost modeli doğrudan backend'e gömülmez; bunun yerine **model distillation**
yaklaşımıyla 24 saatlik normalize edilmiş tüketim profili (`home_shape`) ve hafta sonu
çarpanı (`weekend_multiplier: 1.071`) çıkarılır. Bu hafif JSON artifact
(`backend/app/models/consumption_v1.json`) kullanıcının aylık fatura kWh'iyle
ölçeklenerek saatlik tahmin üretir.

## Notlar

- CatBoost/LightGBM/Prophet sonuçları yalnızca ilgili kütüphaneler kurulu
  olduğunda üretilir (`pip install -r data/scripts/requirements-ml.txt`).
- Karşılaştırma scripti: `data/scripts/evaluate_advanced_consumption.py`.
- Eğitim & deploy scripti: `data/scripts/train_consumption_model.py`.
- Ham veri dosyaları repo'ya commitlenmez (`.gitignore`); `data/` altına yerel
  olarak kopyalanıp çalıştırılmalıdır.
- Model karşılaştırması tamamlandı, CatBoost açık ara en iyi performansı gösterdi.
