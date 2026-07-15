"""Train the final v1 LightGBM production artifact and export it for the backend.

This is the deploy step after data/scripts/compare_production_models.py picked
a winner. Unlike the comparison script (which holds out 2023 to score
candidates), this one trains on ALL available PVGIS years — once a model is
chosen, there's no reason to withhold data from the artifact that actually
ships.

Feature set is identical to compare_production_models.py, which is identical
to what backend/app/tools/production.py has at inference time
(irradiance_wm2, temp_c, cloud_pct -> derived interaction terms). This is
what makes the artifact deployable at all.

Output:
  backend/app/models/production_v1_lgbm.txt   — LightGBM's own text format
                                                  (lgb.Booster.save_model),
                                                  NOT pickle/joblib. Text
                                                  format has no Python/library
                                                  version lock-in — any
                                                  lightgbm >=4.0 can load it.
  backend/app/models/production_v1.json        — small metadata sidecar,
                                                  updated to point at the
                                                  above file and describe how
                                                  to fall back if lightgbm
                                                  isn't installed at runtime.

Usage:
    python data/scripts/train_production_model_lgbm.py \
        --pvgis data/raw/pvgis_hourly.csv \
        --openmeteo data/raw/open_meteo_hourly.csv
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import lightgbm as lgb

# Reuse the exact feature engineering from the comparison script so the
# deployed model was trained the same way it was scored.
sys.path.insert(0, os.path.dirname(__file__))
from compare_production_models import (  # noqa: E402
    FEATURE_COLS,
    engineer_features,
    load_open_meteo_cloud,
    load_pvgis,
)

_BACKEND_MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "backend", "app", "models",
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pvgis", required=True)
    ap.add_argument("--openmeteo", required=True)
    ap.add_argument("--out-dir", default=_BACKEND_MODELS_DIR)
    args = ap.parse_args()

    pv = load_pvgis(args.pvgis)
    cloud = load_open_meteo_cloud(args.openmeteo)
    pv = pv.merge(cloud, on="datetime", how="left")
    pv = engineer_features(pv).sort_values("datetime").reset_index(drop=True)

    X = pv[FEATURE_COLS].values
    y = pv["target_kwh_per_kwp"].values

    model = lgb.LGBMRegressor(
        n_estimators=300, learning_rate=0.05, random_state=42, n_jobs=-1, verbosity=-1,
    )
    model.fit(X, y)

    os.makedirs(args.out_dir, exist_ok=True)
    model_path = os.path.join(args.out_dir, "production_v1_lgbm.txt")
    model.booster_.save_model(model_path)

    meta_path = os.path.join(args.out_dir, "production_v1.json")
    metadata = {
        "model_version": "v1-lightgbm",
        "model_type": "lightgbm",
        "model_file": "production_v1_lgbm.txt",
        "trained_on": f"{args.pvgis} + {args.openmeteo}, full history (no holdout — see "
                       "compare_production_models.py for the held-out evaluation)",
        "target": "hourly AC kWh per installed kWp",
        "features": FEATURE_COLS,
        # Kept for the pure-Python fallback path (no lightgbm installed, or
        # the .txt file is missing) — production.py falls back to this
        # physical/linear blend, matching the original v1-weather-regressor.
        "fallback_performance_ratio": 0.80,
        "max_kw_per_kwp": 1.0,
        "blend_with_physical": 0.0,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        f.write("\n")

    print(f"Trained on {len(pv)} rows.")
    print(f"Wrote {model_path}")
    print(f"Wrote {meta_path}")
    print("\nNext steps:")
    print("  1. Add `lightgbm>=4.0` to backend/requirements.txt (not yet there).")
    print("  2. cd backend && python -m pytest tests/ -v   # confirm nothing broke")
    print("  3. git add backend/app/models/production_v1_lgbm.txt "
          "backend/app/models/production_v1.json backend/requirements.txt")


if __name__ == "__main__":
    main()
