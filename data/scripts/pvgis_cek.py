"""PVGIS saatlik geçmiş veri çekme scripti (VB ekibi — model eğitimi).

Kullanım:
    python pvgis_cek.py --enlem 38.42 --boylam 27.14 --yil-bas 2019 --yil-son 2023 --cikti izmir.csv

Çıktı: saatlik ışınım (G(i), W/m²), sıcaklık ve PVGIS'in kendi PV üretim
tahmini (P, W — 1 kWp referans sistem). LightGBM eğitiminde hedef değişken
olarak P kullanılabilir; Open-Meteo geçmiş verisiyle birleştirip özellik
zenginleştirmesi yapılabilir (bkz. docs/METHOD.md).

PVGIS API ücretsizdir ve anahtar gerektirmez.
"""

import argparse
import csv
import sys

import httpx

# v5_3: SARAH3 veritabanı, 2005-2023 saatlik seri (v5_2 2020'de biter)
URL = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"


def cek(enlem: float, boylam: float, yil_bas: int, yil_son: int) -> list[dict]:
    yanit = httpx.get(URL, params={
        "lat": enlem, "lon": boylam,
        "startyear": yil_bas, "endyear": yil_son,
        "pvcalculation": 1, "peakpower": 1, "loss": 14,
        "outputformat": "json",
    }, timeout=120)
    if yanit.status_code != 200:
        sys.exit(f"PVGIS hatası ({yanit.status_code}): {yanit.text[:200]}")
    return yanit.json()["outputs"]["hourly"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--enlem", type=float, default=38.42)
    ap.add_argument("--boylam", type=float, default=27.14)
    ap.add_argument("--yil-bas", type=int, default=2019)
    ap.add_argument("--yil-son", type=int, default=2023)
    ap.add_argument("--cikti", default="pvgis_saatlik.csv")
    args = ap.parse_args()

    print(f"PVGIS'ten çekiliyor: ({args.enlem}, {args.boylam}) {args.yil_bas}-{args.yil_son}…")
    satirlar = cek(args.enlem, args.boylam, args.yil_bas, args.yil_son)
    if not satirlar:
        sys.exit("Veri boş döndü — koordinatları kontrol edin.")

    with open(args.cikti, "w", newline="", encoding="utf-8") as f:
        yazici = csv.DictWriter(f, fieldnames=satirlar[0].keys())
        yazici.writeheader()
        yazici.writerows(satirlar)
    print(f"{len(satirlar)} saatlik satır → {args.cikti}")


if __name__ == "__main__":
    main()
