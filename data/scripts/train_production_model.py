"""Train the small Voltaic PV production artifact from a PVGIS hourly CSV.

This script intentionally uses only the Python standard library so the team can
run it anywhere:

    python data/scripts/train_production_model.py --csv izmir.csv --out backend/app/models/production_v1.json

Expected PVGIS columns include time, G(i), T2m and P. P is hourly PV output for a
1 kWp reference system, so the learned target is kWh per kWp for that hour.
"""

import argparse
import csv
import json
from datetime import datetime
from io import StringIO


def _float(row: dict, *names: str) -> float:
    for name in names:
        if name in row and row[name] not in ("", None):
            return float(str(row[name]).replace(",", "."))
    return 0.0


def _hour(row: dict) -> int:
    raw = row.get("time") or row.get("Time") or row.get("datetime") or ""
    raw = raw.strip().replace("Z", "")
    candidates = [
        raw,
        raw.replace(":", ""),
        raw.replace("T", " "),
    ]
    for value in candidates:
        for fmt in ("%Y%m%d%H%M", "%Y%m%d%H", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(value, fmt).hour
            except ValueError:
                continue
    if len(raw) >= 4 and raw[-4:-2].isdigit():
        try:
            return int(raw[-4:-2])
        except ValueError:
            return 12
    return 12


def _features(row: dict) -> list[float]:
    ghi = _float(row, "G(i)", "G(h)", "shortwave_radiation", "irradiance")
    temp = _float(row, "T2m", "temperature_2m", "temp")
    cloud = _float(row, "cloud_cover", "cloud", "cloud_pct")
    hour = _hour(row)
    edge_loss = abs(hour - 12) / 12
    return [
        ghi,
        ghi * max(temp - 25.0, 0.0),
        ghi * cloud,
        edge_loss,
    ]


def _target(row: dict) -> float:
    # PVGIS P is W for a 1 kWp system. One hourly row -> Wh, so /1000 = kWh.
    return max(_float(row, "P", "pv_output", "production_w") / 1000.0, 0.0)


def _solve_linear_system(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    for i in range(n):
        pivot = max(range(i, n), key=lambda r: abs(a[r][i]))
        a[i], a[pivot] = a[pivot], a[i]
        b[i], b[pivot] = b[pivot], b[i]
        div = a[i][i] or 1e-12
        for j in range(i, n):
            a[i][j] /= div
        b[i] /= div
        for r in range(n):
            if r == i:
                continue
            factor = a[r][i]
            for c in range(i, n):
                a[r][c] -= factor * a[i][c]
            b[r] -= factor * b[i]
    return b


def _fit(rows: list[dict], ridge: float = 0.01) -> list[float]:
    x_rows = [[1.0, *_features(row)] for row in rows if _target(row) > 0 or _features(row)[0] > 0]
    y = [_target(row) for row in rows if _target(row) > 0 or _features(row)[0] > 0]
    n_features = len(x_rows[0])
    xtx = [[0.0] * n_features for _ in range(n_features)]
    xty = [0.0] * n_features
    for x, target in zip(x_rows, y):
        for i in range(n_features):
            xty[i] += x[i] * target
            for j in range(n_features):
                xtx[i][j] += x[i] * x[j]
    for i in range(1, n_features):
        xtx[i][i] += ridge
    return _solve_linear_system(xtx, xty)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--out", default="backend/app/models/production_v1.json")
    args = parser.parse_args()

    with open(args.csv, encoding="utf-8-sig") as f:
        content = "".join(line for line in f if line.strip())
        rows = list(csv.DictReader(StringIO(content)))
    coef = _fit(rows)
    artifact = {
        "model_version": "v1-weather-regressor",
        "trained_on": args.csv,
        "target": "hourly AC kWh per installed kWp",
        "features": [
            "shortwave_radiation_wm2",
            "temperature_loss_interaction",
            "cloud_interaction",
            "edge_hour_loss",
        ],
        "intercept": round(coef[0], 8),
        "coefficients": {
            "ghi": round(coef[1], 10),
            "temp_loss": round(coef[2], 12),
            "cloud_interaction": round(coef[3], 12),
            "edge_hour_loss": round(coef[4], 8),
        },
        "fallback_performance_ratio": 0.80,
        "max_kw_per_kwp": 1.0,
        "blend_with_physical": 0.25,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)
        f.write("\n")
    print(f"Wrote {args.out} from {len(rows)} hourly rows")


if __name__ == "__main__":
    main()
