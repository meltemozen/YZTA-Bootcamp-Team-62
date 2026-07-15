"""Compare candidate ML models for hourly PV production forecasting.

Scope (Sprint 2 — "LightGBM Üretim Modeli (v1) Geliştirimi"):
Only the PRODUCTION model is evaluated here (irradiance / temperature / cloud
cover -> kWh per installed kWp). Consumption modelling is a separate task.

Models compared:
  - v0-physical   : the formula already live in backend/app/tools/production.py
                    (PV_PERFORMANCE_RATIO / PV_TEMP_COEFF / PV_NOCT_FACTOR),
                    used as the baseline every candidate must beat.
  - Ridge          : linear baseline (scikit-learn), same features as v0-linear.
  - RandomForest   : non-parametric baseline, low tuning sensitivity.
  - LightGBM       : primary candidate.
  - XGBoost        : secondary candidate / sanity check on LightGBM.

Split: last calendar year held out (time-based, not shuffled) per docs/METHOD.md
("son yıl hold-out, nMAE; v0 baseline'ı geçemeyen model üretime alınmaz").

Usage:
    python data/scripts/compare_production_models.py \
        --pvgis "data/raw/PVGIS Saatlik Veri (Hourly Data).csv" \
        --meteo "data/raw/open-meteo-38.49N27.11E114m.csv" \
        --nasa  "data/raw/NASA POWER.csv" \
        --report docs/research/PRODUCTION_MODEL_COMPARISON.md \
        --save-best backend/app/models/production_v1_candidate.joblib

Requires: pandas, numpy, scikit-learn (already in requirements-dev), plus
lightgbm and xgboost (see data/scripts/requirements-ml.txt).
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore")

# Physical model constants — kept in sync with backend/app/config.py so the
# v0 baseline computed here is identical to what's live in production.
PV_PERFORMANCE_RATIO = 0.80
PV_TEMP_COEFF = 0.004
PV_NOCT_FACTOR = 0.03


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #

def load_open_meteo(filepath: str) -> pd.DataFrame:
    """Open-Meteo hourly weather export (3 metadata rows, then header)."""
    df = pd.read_csv(filepath, skiprows=3)
    df["datetime"] = pd.to_datetime(df["time"]).dt.floor("h")
    temp_col = next(c for c in df.columns if c.startswith("temperature_2m"))
    cloud_col = next(c for c in df.columns if c.startswith("cloud_cover"))
    df = df[["datetime", temp_col, cloud_col]].rename(
        columns={temp_col: "meteo_temp", cloud_col: "meteo_cloud_pct"}
    )
    return df.groupby("datetime", as_index=False).mean()


def load_pvgis(filepath: str) -> pd.DataFrame:
    """PVGIS hourly export. G(i) isn't a direct column — it's the sum of the
    beam/diffuse/reflected components (Gb(i) + Gd(i) + Gr(i))."""
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()
    header_idx = next(i for i, line in enumerate(lines) if line.startswith("time,P,"))

    df = pd.read_csv(filepath, skiprows=header_idx, engine="python", on_bad_lines="skip")
    df = df.dropna(subset=["time"])
    df["datetime"] = pd.to_datetime(df["time"].astype(str), format="%Y%m%d:%H%M", errors="coerce")
    df = df.dropna(subset=["datetime"]).copy()
    df["datetime"] = df["datetime"].dt.floor("h")

    for col in ["P", "Gb(i)", "Gd(i)", "Gr(i)", "T2m"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["radiation"] = df["Gb(i)"] + df["Gd(i)"] + df["Gr(i)"]
    df = df.rename(columns={"P": "target_production_w", "T2m": "pvgis_temp"})
    df = df[["datetime", "target_production_w", "radiation", "pvgis_temp"]]
    return df.groupby("datetime", as_index=False).mean()


def load_nasa_power(filepath: str) -> pd.DataFrame:
    with open(filepath, encoding="utf-8") as f:
        skip_idx = next(i for i, line in enumerate(f) if "YEAR" in line and "MO" in line)
    df = pd.read_csv(filepath, skiprows=skip_idx)
    df["datetime"] = pd.to_datetime(
        df[["YEAR", "MO", "DY", "HR"]].rename(
            columns={"YEAR": "year", "MO": "month", "DY": "day", "HR": "hour"}
        )
    ).dt.floor("h")
    df = df.replace(-999, np.nan)
    feature_cols = [c for c in df.columns if c not in ("YEAR", "MO", "DY", "HR", "datetime")]
    df = df[["datetime"] + feature_cols].rename(columns={c: f"nasa_{c}" for c in feature_cols})
    return df.groupby("datetime", as_index=False).mean()


def merge_and_engineer(meteo_path: str, pvgis_path: str, nasa_path: str) -> pd.DataFrame:
    df = load_pvgis(pvgis_path)
    df = df.merge(load_open_meteo(meteo_path), on="datetime", how="inner")
    df = df.merge(load_nasa_power(nasa_path), on="datetime", how="inner")

    # PVGIS P is watts for a 1 kWp reference system -> kWh per kWp per hour.
    df["target_kwh_per_kwp"] = (df["target_production_w"] / 1000.0).clip(lower=0.0)

    df["hour"] = df["datetime"].dt.hour
    df["month"] = df["datetime"].dt.month
    df["year"] = df["datetime"].dt.year
    df["doy"] = df["datetime"].dt.dayofyear
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["doy_sin"] = np.sin(2 * np.pi * df["doy"] / 365)
    df["doy_cos"] = np.cos(2 * np.pi * df["doy"] / 365)

    # Night-time rows are true zeros, not missing data.
    df.loc[df["radiation"] < 5, "target_kwh_per_kwp"] = 0.0
    return df.dropna().sort_values("datetime").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Baselines & metrics
# --------------------------------------------------------------------------- #

def physical_baseline(radiation: np.ndarray, temp: np.ndarray) -> np.ndarray:
    """Exact port of backend/app/tools/production.py::_physical_kw_per_kwp."""
    cell_temp = temp + PV_NOCT_FACTOR * radiation
    temp_factor = 1 - PV_TEMP_COEFF * np.maximum(0.0, cell_temp - 25)
    return np.maximum(0.0, (radiation / 1000.0) * PV_PERFORMANCE_RATIO * temp_factor)


def nmae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """MAE normalised by the mean of the (daylight-hour) target, in %."""
    daylight = y_true > 0.01
    if daylight.sum() == 0:
        return float("nan")
    return float(
        mean_absolute_error(y_true[daylight], y_pred[daylight]) / y_true[daylight].mean() * 100
    )


def evaluate(name: str, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_pred = np.clip(y_pred, 0.0, None)
    return {
        "model": name,
        "MAE": round(mean_absolute_error(y_true, y_pred), 5),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 5),
        "nMAE_%": round(nmae(y_true, y_pred), 2),
    }


# --------------------------------------------------------------------------- #
# Main comparison
# --------------------------------------------------------------------------- #

FEATURE_COLS = [
    "radiation", "meteo_temp", "meteo_cloud_pct", "pvgis_temp",
    "hour_sin", "hour_cos", "doy_sin", "doy_cos", "month",
]


def run_comparison(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    last_year = df["year"].max()
    train = df[df["year"] < last_year]
    test = df[df["year"] == last_year]
    if len(test) < 500:  # not enough data for a clean full-year holdout
        split = int(len(df) * 0.8)
        train, test = df.iloc[:split], df.iloc[split:]

    X_train, y_train = train[FEATURE_COLS], train["target_kwh_per_kwp"].to_numpy()
    X_test, y_test = test[FEATURE_COLS], test["target_kwh_per_kwp"].to_numpy()

    results = []
    fitted = {}

    # v0 — physical formula already in production, zero training cost.
    v0_pred = physical_baseline(test["radiation"].to_numpy(), test["meteo_temp"].to_numpy())
    results.append(evaluate("v0-physical (baseline)", y_test, v0_pred))

    ridge = Ridge(alpha=1.0).fit(X_train, y_train)
    results.append(evaluate("Ridge", y_test, ridge.predict(X_test)))
    fitted["Ridge"] = ridge

    rf = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    results.append(evaluate("RandomForest", y_test, rf.predict(X_test)))
    fitted["RandomForest"] = rf

    try:
        import lightgbm as lgb
        lgbm = lgb.LGBMRegressor(
            random_state=42, n_estimators=400, learning_rate=0.05,
            num_leaves=31, n_jobs=-1, verbosity=-1,
        )
        lgbm.fit(X_train, y_train)
        results.append(evaluate("LightGBM", y_test, lgbm.predict(X_test)))
        fitted["LightGBM"] = lgbm
    except ImportError:
        print("[skip] lightgbm not installed — run: pip install -r data/scripts/requirements-ml.txt")

    try:
        import xgboost as xgb
        xgbr = xgb.XGBRegressor(
            random_state=42, n_estimators=400, learning_rate=0.05,
            max_depth=6, objective="reg:squarederror", n_jobs=-1,
        )
        xgbr.fit(X_train, y_train)
        results.append(evaluate("XGBoost", y_test, xgbr.predict(X_test)))
        fitted["XGBoost"] = xgbr
    except ImportError:
        print("[skip] xgboost not installed — run: pip install -r data/scripts/requirements-ml.txt")

    results_df = pd.DataFrame(results).sort_values("nMAE_%")
    return results_df, fitted


def write_report(results_df: pd.DataFrame, df: pd.DataFrame, out_path: str) -> None:
    last_year = df["year"].max()
    beats_baseline = results_df[results_df["model"] != "v0-physical (baseline)"].iloc[0]
    baseline_row = results_df[results_df["model"] == "v0-physical (baseline)"].iloc[0]
    winner_beats_v0 = beats_baseline["nMAE_%"] < baseline_row["nMAE_%"]

    ran_models = set(results_df["model"])
    missing = [m for m in ("LightGBM", "XGBoost") if m not in ran_models]

    lines = ["# Üretim Modeli Karşılaştırması (v1)", ""]
    if missing:
        lines += [
            f"> ⚠️ Bu çalıştırmada **{', '.join(missing)} kurulu değildi**, bu yüzden tabloda yer "
            "almıyor. `pip install -r data/scripts/requirements-ml.txt` sonrası scripti tekrar "
            "çalıştırıp bu raporu güncelleyin — nihai model seçimi bu ikisi olmadan kesinleştirilmemeli.",
            "",
        ]
    lines += [
        f"- Veri: PVGIS (hedef + ışınım) + Open-Meteo + NASA POWER, saatlik, İzmir bölgesi.",
        f"- Doğrulama: son yıl hold-out ({last_year}), zaman bazlı split (shuffle yok).",
        "- Metrikler: MAE / RMSE (kWh/kWp), nMAE % (yalnızca gündüz saatleri, radiation > 0).",
        "- Kural (docs/METHOD.md): v0-physical baseline'ı geçemeyen model üretime alınmaz.",
        "",
        "## Sonuçlar",
        "",
        "| Model | MAE | RMSE | nMAE % |",
        "|---|---|---|---|",
    ]
    for _, r in results_df.iterrows():
        lines.append(f"| {r['model']} | {r['MAE']} | {r['RMSE']} | {r['nMAE_%']} |")

    lines += [
        "",
        "## Karar",
        "",
    ]
    if winner_beats_v0:
        lines.append(
            f"**{beats_baseline['model']}** en düşük nMAE'ye sahip ve v0-physical baseline'ı "
            f"({baseline_row['nMAE_%']}%) geçiyor ({beats_baseline['nMAE_%']}%). "
            "v1 adayı olarak önerilir."
        )
    else:
        lines.append(
            "Hiçbir ML adayı v0-physical baseline'ı geçemedi "
            f"(en iyi aday {beats_baseline['model']}: {beats_baseline['nMAE_%']}% vs "
            f"baseline {baseline_row['nMAE_%']}%). METHOD.md kuralı gereği v0 fiziksel model "
            "üretimde kalmaya devam etmeli; ek özellik mühendisliği veya daha fazla veri gerekiyor."
        )
    lines += [
        "",
        "## Notlar",
        "",
        "- LightGBM/XGBoost sonuçları yalnızca bu kütüphaneler kurulu olduğunda üretilir "
        "(`pip install -r data/scripts/requirements-ml.txt`).",
        "- Script: `data/scripts/compare_production_models.py`.",
        "- Ham veri dosyaları repo'ya commitlenmez (`.gitignore`); `data/raw/` altına yerel olarak "
        "kopyalanıp çalıştırılmalıdır.",
    ]

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written to {out_path}")


def save_best_model(results_df: pd.DataFrame, fitted: dict, out_path: str) -> None:
    non_baseline = results_df[results_df["model"] != "v0-physical (baseline)"]
    if non_baseline.empty:
        return
    best_name = non_baseline.iloc[0]["model"]
    model = fitted.get(best_name)
    if model is None:
        return
    import joblib
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model_name": best_name, "features": FEATURE_COLS, "model": model}, out_path)
    print(f"Best candidate ({best_name}) saved to {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pvgis", required=True)
    ap.add_argument("--meteo", required=True)
    ap.add_argument("--nasa", required=True)
    ap.add_argument("--report", default="docs/research/PRODUCTION_MODEL_COMPARISON.md")
    ap.add_argument("--save-best", default=None, help="Optional joblib output path")
    ap.add_argument("--results-json", default=None, help="Optional raw metrics JSON output path")
    args = ap.parse_args()

    print("Loading and merging datasets...")
    df = merge_and_engineer(args.meteo, args.pvgis, args.nasa)
    print(f"{len(df)} merged hourly rows, {df['year'].min()}–{df['year'].max()}")

    print("Training and evaluating models...")
    results_df, fitted = run_comparison(df)
    print(results_df.to_string(index=False))

    write_report(results_df, df, args.report)
    if args.save_best:
        save_best_model(results_df, fitted, args.save_best)
    if args.results_json:
        Path(args.results_json).write_text(results_df.to_json(orient="records", indent=2))


if __name__ == "__main__":
    main()
