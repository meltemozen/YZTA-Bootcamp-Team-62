"""PVGIS hourly historical data fetch script (DS team — model training).

Usage:
    python pvgis_fetch.py --lat 38.42 --lon 27.14 --start-year 2019 --end-year 2023 --out izmir.csv

Output: hourly irradiance (G(i), W/m²), temperature and PVGIS's own PV
production estimate (P, W — 1 kWp reference system). P can be used as the
target variable in LightGBM training; it can be joined with Open-Meteo history
for feature enrichment (see docs/METHOD.md).

The PVGIS API is free and requires no key.
"""

import argparse
import csv
import sys

import httpx

# v5_3: SARAH3 database, hourly series 2005-2023 (v5_2 ends in 2020)
URL = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"


def fetch(lat: float, lon: float, start_year: int, end_year: int) -> list[dict]:
    resp = httpx.get(URL, params={
        "lat": lat, "lon": lon,
        "startyear": start_year, "endyear": end_year,
        "pvcalculation": 1, "peakpower": 1, "loss": 14,
        "outputformat": "json",
    }, timeout=120)
    if resp.status_code != 200:
        sys.exit(f"PVGIS error ({resp.status_code}): {resp.text[:200]}")
    return resp.json()["outputs"]["hourly"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=38.42)
    ap.add_argument("--lon", type=float, default=27.14)
    ap.add_argument("--start-year", type=int, default=2019)
    ap.add_argument("--end-year", type=int, default=2023)
    ap.add_argument("--out", default="pvgis_hourly.csv")
    args = ap.parse_args()

    print(f"Fetching from PVGIS: ({args.lat}, {args.lon}) {args.start_year}-{args.end_year}…")
    rows = fetch(args.lat, args.lon, args.start_year, args.end_year)
    if not rows:
        sys.exit("Empty data returned — check the coordinates.")

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} hourly rows → {args.out}")


if __name__ == "__main__":
    main()
