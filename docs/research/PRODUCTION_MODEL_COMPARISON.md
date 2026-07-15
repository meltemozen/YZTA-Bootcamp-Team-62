# Üretim Modeli Karşılaştırması (v1)

> ⚠️ Bu çalıştırmada **LightGBM, XGBoost kurulu değildi**, bu yüzden tabloda yer almıyor. `pip install -r data/scripts/requirements-ml.txt` sonrası scripti tekrar çalıştırıp bu raporu güncelleyin — nihai model seçimi bu ikisi olmadan kesinleştirilmemeli.

- Veri: PVGIS (hedef + ışınım) + Open-Meteo + NASA POWER, saatlik, İzmir bölgesi.
- Doğrulama: son yıl hold-out (2023), zaman bazlı split (shuffle yok).
- Metrikler: MAE / RMSE (kWh/kWp), nMAE % (yalnızca gündüz saatleri, radiation > 0).
- Kural (docs/METHOD.md): v0-physical baseline'ı geçemeyen model üretime alınmaz.

## Sonuçlar

| Model | MAE | RMSE | nMAE % |
|---|---|---|---|
| RandomForest | 0.00175 | 0.00426 | 1.09 |
| Ridge | 0.00725 | 0.01214 | 3.62 |
| v0-physical (baseline) | 0.01006 | 0.01871 | 6.13 |

## Karar

**RandomForest** en düşük nMAE'ye sahip ve v0-physical baseline'ı (6.13%) geçiyor (1.09%). v1 adayı olarak önerilir.

## Notlar

- LightGBM/XGBoost sonuçları yalnızca bu kütüphaneler kurulu olduğunda üretilir (`pip install -r data/scripts/requirements-ml.txt`).
- Script: `data/scripts/compare_production_models.py`.
- Ham veri dosyaları repo'ya commitlenmez (`.gitignore`); `data/raw/` altına yerel olarak kopyalanıp çalıştırılmalıdır.
