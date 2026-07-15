# Üretim Modeli Karşılaştırması (v1)

- Veri: PVGIS (hedef `P` + `Gb(i)`/`Gd(i)`/`Gr(i)`) + Open-Meteo (`cloud_cover`), saatlik.
- Doğrulama: son yıl hold-out (2023), zaman bazlı split (shuffle yok).
- Özellikler: `irradiance_wm2`, `temp_loss_interaction`, `cloud_interaction`, `edge_hour_loss`
  — backend'in çalışma zamanında (`forecast_production`) sahip olduğu girdilerle bire bir aynı,
  böylece kazanan model doğrudan deploy edilebilir.
- Metrikler: MAE / RMSE (kWh/kWp), nMAE % (yalnızca gündüz saatleri, irradiance > 0).
- Kural (docs/METHOD.md): v0-physical baseline'ı geçemeyen model üretime alınmaz.

## Sonuçlar

| Model | MAE | RMSE | nMAE % |
|---|---|---|---|
| LightGBM | 0.00335 | 0.00771 | 2.08 |
| XGBoost | 0.00337 | 0.00775 | 2.09 |
| RandomForest | 0.00343 | 0.00801 | 2.13 |
| Ridge | 0.00581 | 0.01109 | 3.60 |
| v0-physical (baseline) | 0.00882 | 0.01605 | 5.47 |

## Karar

**LightGBM** en düşük nMAE'ye sahip ve v0-physical baseline'ı (5.47%) geçiyor.

## Notlar

- LightGBM/XGBoost sonuçları yalnızca bu kütüphaneler kurulu olduğunda üretilir
  (`pip install -r data/scripts/requirements-ml.txt`).
- Script: `data/scripts/compare_production_models.py`.
- Ham veri dosyaları repo'ya commitlenmez (`.gitignore`); `data/raw/` altına yerel
  olarak kopyalanıp çalıştırılmalıdır.

- Model karşılaştırması tamamlandı, LightGBM/XGBoost/RandomForest pratikte eşdeğer (~%2 nMAE), hepsi baseline'ı geçti.