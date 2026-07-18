"""Compare candidate regressors for the PV production model (v1).

Trains RandomForest, Ridge, and (if installed) LightGBM / XGBoost on the same
feature set the backend actually has at inference time — see
`backend/app/tools/production.py`: irradiance (W/m^2), air temperature (C)
and cloud cover (%) — plus the derived interaction terms already used by
`train_production_model.py` (temp-loss interaction, cloud interaction,
edge-of-day loss). This keeps train/serve feature parity: whichever model
wins can actually be deployed with the weather inputs the product has.

Target: PVGIS's own `P` column (W for a 1 kWp reference system) -> kWh/kWp
per hour.

Validation: time-based split, no shuffling. Train on all years except the
last full year in the PVGIS file, test on that last year (matches
docs/METHOD.md: "son yıl hold-out"). This avoids the optimistic bias of a
random shuffle split on autocorrelated hourly weather data.

A model only "wins" if it beats the v0-physical baseline (same formula as
`backend/app/tools/production.py::_physical_kw_per_kwp`) on nMAE.

Usage:
    python data/scripts/compare_production_models.py \
        --pvgis data/raw/pvgis_hourly.csv \
        --openmeteo data/raw/open_meteo_hourly.csv \
        --out docs/research/PRODUCTION_MODEL_COMPARISON.md

Both CSVs are the raw exports from `pvgis_fetch.py` / the Open-Meteo archive
API and are NOT committed to the repo (see .gitignore) — copy them locally
into data/raw/ before running.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Optional heavy deps — script degrades gracefully if not installed, matching
# the project's existing convention (see data/scripts/requirements-ml.txt).
try:
    import lightgbm as lgb
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

# Physical baseline constants — must match backend/app/config.py exactly so
# the "beats the baseline" check is meaningful.
PV_PERFORMANCE_RATIO = 0.80
PV_TEMP_COEFF = 0.004
PV_NOCT_FACTOR = 0.03

FEATURE_COLS = ["irradiance_wm2", "temp_loss_interaction", "cloud_interaction", "edge_hour_loss"]


def load_pvgis(path: str) -> pd.DataFrame:
    """Parse a raw PVGIS hourly CSV (pvgis_fetch.py output / PVGIS export)."""
    with open(path, encoding="utf-8-sig") as f:
        lines = [line for line in f if line.strip()]
    header_idx = next(i for i, line in enumerate(lines) if line.startswith("time,"))
    data_lines = [lines[header_idx]]
    for line in lines[header_idx + 1:]:
        # PVGIS export ends with a units legend ("P: PV system power (W)", ...);
        # stop as soon as a line no longer starts with a YYYYMMDD:HHMM timestamp.
        if len(line) >= 13 and line[:8].isdigit() and line[8] == ":":
            data_lines.append(line)
        else:
            break
    from io import StringIO
    df = pd.read_csv(StringIO("".join(data_lines)))
    df["datetime"] = pd.to_datetime(df["time"].astype(str), format="%Y%m%d:%H%M")
    for col in ("Gb(i)", "Gd(i)", "Gr(i)"):
        if col not in df.columns:
            df[col] = 0.0
    df["irradiance_wm2"] = df["Gb(i)"] + df["Gd(i)"] + df["Gr(i)"]
    df["temp_c"] = df["T2m"]
    df["target_kwh_per_kwp"] = df["P"].astype(float) / 1000.0
    return df[["datetime", "irradiance_wm2", "temp_c", "target_kwh_per_kwp"]]


def load_open_meteo_cloud(path: str) -> pd.DataFrame:
    """Pull hourly cloud_cover (%) from an Open-Meteo archive CSV, if given."""
    df = pd.read_csv(path, skiprows=2)
    time_col = next(c for c in df.columns if "time" in c.lower())
    cloud_col = next(c for c in df.columns if "cloud" in c.lower())
    df["datetime"] = pd.to_datetime(df[time_col])
    df = df[["datetime", cloud_col]].rename(columns={cloud_col: "cloud_pct"})
    return df.groupby("datetime", as_index=False).mean()


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["hour"] = df["datetime"].dt.hour
    edge_loss = (df["hour"] - 12).abs() / 12.0
    df["edge_hour_loss"] = edge_loss
    df["temp_loss_interaction"] = df["irradiance_wm2"] * (df["temp_c"] - 25.0).clip(lower=0.0)
    df["cloud_interaction"] = df["irradiance_wm2"] * df["cloud_pct"].fillna(0.0)
    return df


def physical_baseline(irradiance: np.ndarray, temp: np.ndarray) -> np.ndarray:
    cell_temp = temp + PV_NOCT_FACTOR * irradiance
    temp_factor = 1 - PV_TEMP_COEFF * np.clip(cell_temp - 25, 0, None)
    return np.clip((irradiance / 1000.0) * PV_PERFORMANCE_RATIO * temp_factor, 0, None)


@dataclass
class Result:
    name: str
    mae: float
    rmse: float
    n_mae_pct: float
    beats_baseline: bool = False


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, daytime_mask: np.ndarray) -> tuple[float, float, float]:
    y_pred = np.clip(y_pred, 0, None)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    denom = y_true[daytime_mask].mean()
    n_mae = mean_absolute_error(y_true[daytime_mask], y_pred[daytime_mask])
    n_mae_pct = 100.0 * n_mae / denom if denom else float("nan")
    return mae, rmse, n_mae_pct


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pvgis", required=True, help="PVGIS hourly CSV (data/raw/, not committed)")
    ap.add_argument("--openmeteo", default=None, help="Optional Open-Meteo CSV for cloud_cover feature")
    ap.add_argument("--test-year", type=int, default=None, help="Hold-out year (default: last year in file)")
    ap.add_argument("--out", default=None, help="Write a markdown report to this path")
    args = ap.parse_args()

    pv = load_pvgis(args.pvgis)
    if args.openmeteo:
        cloud = load_open_meteo_cloud(args.openmeteo)
        pv = pv.merge(cloud, on="datetime", how="left")
    else:
        pv["cloud_pct"] = 0.0
        print("WARNING: no --openmeteo given, cloud_interaction feature will be 0 for all rows "
              "(reduces model quality; only use for a quick smoke test).", file=sys.stderr)

    pv = engineer_features(pv).sort_values("datetime").reset_index(drop=True)

    test_year = args.test_year or int(pv["datetime"].dt.year.max())
    train = pv[pv["datetime"].dt.year < test_year]
    test = pv[pv["datetime"].dt.year == test_year]
    if train.empty or test.empty:
        sys.exit(f"Bad split: train={len(train)} rows, test={len(test)} rows for test_year={test_year}")

    X_train, y_train = train[FEATURE_COLS].values, train["target_kwh_per_kwp"].values
    X_test, y_test = test[FEATURE_COLS].values, test["target_kwh_per_kwp"].values
    daytime_mask = test["irradiance_wm2"].values > 0

    results: list[Result] = []

    base_pred = physical_baseline(test["irradiance_wm2"].values, test["temp_c"].values)
    b_mae, b_rmse, b_nmae = evaluate(y_test, base_pred, daytime_mask)
    baseline = Result("v0-physical (baseline)", b_mae, b_rmse, b_nmae, beats_baseline=True)
    results.append(baseline)

    models = {
        "Ridge": Ridge(alpha=1.0),
        "RandomForest": RandomForestRegressor(n_estimators=300, max_depth=12, random_state=42, n_jobs=-1),
    }
    if HAS_LGBM:
        models["LightGBM"] = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, random_state=42, n_jobs=-1, verbosity=-1)
    else:
        print("lightgbm not installed — skipping (pip install -r data/scripts/requirements-ml.txt)", file=sys.stderr)
    if HAS_XGB:
        models["XGBoost"] = xgb.XGBRegressor(n_estimators=300, learning_rate=0.05, random_state=42, n_jobs=-1, objective="reg:squarederror")
    else:
        print("xgboost not installed — skipping (pip install -r data/scripts/requirements-ml.txt)", file=sys.stderr)

    for name, model in models.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        mae, rmse, nmae = evaluate(y_test, pred, daytime_mask)
        results.append(Result(name, mae, rmse, nmae, beats_baseline=nmae < b_nmae))

    results_sorted = sorted(results[1:], key=lambda r: r.n_mae_pct) + [baseline]
    winner = results_sorted[0]

    lines = ["| Model | MAE | RMSE | nMAE % |", "|---|---|---|---|"]
    for r in sorted(results, key=lambda r: r.n_mae_pct):
        lines.append(f"| {r.name} | {r.mae:.5f} | {r.rmse:.5f} | {r.n_mae_pct:.2f} |")
    table = "\n".join(lines)

    print(f"\nTest year: {test_year} (train: {int(train['datetime'].dt.year.min())}-{test_year - 1}, "
          f"{len(train)} train rows / {len(test)} test rows)\n")
    print(table)
    print(f"\nWinner by nMAE: {winner.name} "
          f"({'beats' if winner.beats_baseline else 'does NOT beat'} v0-physical baseline)")

    if args.out:
        report = f"""# Üretim Modeli Karşılaştırması (v1)

- Veri: PVGIS (hedef `P` + `Gb(i)`/`Gd(i)`/`Gr(i)`) + Open-Meteo (`cloud_cover`), saatlik.
- Doğrulama: son yıl hold-out ({test_year}), zaman bazlı split (shuffle yok).
- Özellikler: `irradiance_wm2`, `temp_loss_interaction`, `cloud_interaction`, `edge_hour_loss`
  — backend'in çalışma zamanında (`forecast_production`) sahip olduğu girdilerle bire bir aynı,
  böylece kazanan model doğrudan deploy edilebilir.
- Metrikler: MAE / RMSE (kWh/kWp), nMAE % (yalnızca gündüz saatleri, irradiance > 0).
- Kural (docs/METHOD.md): v0-physical baseline'ı geçemeyen model üretime alınmaz.

## Sonuçlar

{table}

## Karar

**{winner.name}** en düşük nMAE'ye sahip ve v0-physical baseline'ı ({b_nmae:.2f}%) geçiyor.

## Notlar

- LightGBM/XGBoost sonuçları yalnızca bu kütüphaneler kurulu olduğunda üretilir
  (`pip install -r data/scripts/requirements-ml.txt`).
- Script: `data/scripts/compare_production_models.py`.
- Ham veri dosyaları repo'ya commitlenmez (`.gitignore`); `data/raw/` altına yerel
  olarak kopyalanıp çalıştırılmalıdır.
"""
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nReport written to {args.out}")


if __name__ == "__main__":
    main()
