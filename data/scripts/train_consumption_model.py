"""Build the generic hourly consumption-shape artifact from smart-meter CSV data.

The script accepts common column names and writes the 24-hour normalized shape.
Scale is deliberately NOT learned here; runtime scale comes from the user's bill.

    python data/scripts/train_consumption_model.py --csv smart_meter.csv --out backend/app/models/consumption_v1.json
"""

import argparse
import csv
import json
from datetime import datetime
from io import StringIO


def _parse_hour(row: dict) -> int | None:
    raw = row.get("timestamp") or row.get("datetime") or row.get("date_time") or row.get("time")
    if not raw:
        return None
    raw = raw.replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M"):
        try:
            return datetime.strptime(raw, fmt).hour
        except ValueError:
            continue
    return None


def _kwh(row: dict) -> float:
    for name in ("kwh", "energy_kwh", "consumption_kwh", "KWH/hh (per half hour) "):
        if name in row and row[name] not in ("", None):
            return max(float(str(row[name]).replace(",", ".")), 0.0)
    return 0.0


def _normalize(values: list[float]) -> list[float]:
    total = sum(values) or 1.0
    return [round(v / total, 6) for v in values]


DEFAULT_HOME = [
    0.026, 0.023, 0.021, 0.020, 0.021, 0.025,
    0.036, 0.045, 0.046, 0.042, 0.039, 0.038,
    0.040, 0.041, 0.041, 0.043, 0.047, 0.057,
    0.071, 0.081, 0.083, 0.076, 0.058, 0.044,
]

DEFAULT_BUSINESS = [
    0.010, 0.009, 0.009, 0.009, 0.010, 0.012,
    0.023, 0.046, 0.078, 0.088, 0.090, 0.089,
    0.086, 0.085, 0.087, 0.086, 0.079, 0.065,
    0.046, 0.032, 0.021, 0.014, 0.013, 0.012,
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--out", default="backend/app/models/consumption_v1.json")
    parser.add_argument("--user-type", choices=["home", "business"], default="home")
    args = parser.parse_args()

    hourly = [0.0] * 24
    rows_seen = 0
    with open(args.csv, encoding="utf-8-sig") as f:
        content = "".join(line for line in f if line.strip())
        for row in csv.DictReader(StringIO(content)):
            hour = _parse_hour(row)
            if hour is None:
                continue
            hourly[hour] += _kwh(row)
            rows_seen += 1

    shape = _normalize(hourly)
    if args.user_type == "business":
        home_shape = DEFAULT_HOME
        business_shape = shape
    else:
        home_shape = shape
        business_shape = DEFAULT_BUSINESS

    artifact = {
        "model_version": "v1-generic-load-shape",
        "trained_on": args.csv,
        "target": "hourly base-load share",
        "home_shape": home_shape,
        "business_shape": business_shape,
        "seasonality": {"home_amplitude": 0.11, "business_amplitude": 0.16},
        "weekend": {"home_multiplier": 1.04, "business_multiplier": 0.72},
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)
        f.write("\n")
    print(f"Wrote {args.out} from {rows_seen} rows")


if __name__ == "__main__":
    main()
