"""Smoke test a deployed Wattra backend.

Usage:
    python backend/scripts/smoke_deploy.py https://your-api.example.com

The script creates a throwaway account, verifies auth isolation is usable, then
hits the product-critical plan/report endpoints and verifies that internal model
metadata is protected. It exits non-zero on the
first failing check, which makes it suitable for CI or a pre-build checklist.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from datetime import date

import httpx


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url", help="Backend URL, e.g. https://wattra-api.example.com")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    email = f"smoke-{secrets.token_hex(4)}@wattra.dev"
    password = "SmokeTest123"
    profile = {
        "user_type": "home",
        "city": "Izmir",
        "lat": 38.42,
        "lon": 27.14,
        "panel_kw": 5.0,
        "battery_kwh": 0,
        "battery_power_kw": 0,
        "monthly_bill_kwh": 300,
        "tariff_type": "three_zone",
        "custom_tariff": {
            "day": 2.5,
            "peak": 4.0,
            "night": 1.5,
            "sell": 1.0,
        },
        "devices": [
            {
                "name": "Camasir makinesi",
                "kwh": 1.0,
                "duration_h": 2,
                "earliest": 8,
                "latest": 23,
            }
        ],
    }

    with httpx.Client(base_url=base, timeout=30) as client:
        health = client.get("/api/health")
        _check(health.status_code == 200, f"health failed: {health.status_code} {health.text}")
        _check(health.json().get("status") == "ok", f"bad health payload: {health.text}")

        model_versions = client.get("/api/model-versions")
        _check(
            model_versions.status_code == 401,
            f"model metadata must require admin auth: {model_versions.status_code}",
        )

        weather = client.get(
            "/api/weather-check",
            params={"lat": 38.42, "lon": 27.14, "panel_kw": 5, "day": "today"},
        )
        _check(
            weather.status_code == 401,
            f"weather diagnostics must require admin auth: {weather.status_code}",
        )

        register = client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "name": "Smoke Test", "profile": profile},
        )
        _check(register.status_code == 200, f"register failed: {register.status_code} {register.text}")
        body = register.json()
        token = body["access_token"]
        user_id = body["user_id"]
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get("/api/auth/me", headers=headers)
        _check(me.status_code == 200, f"auth/me failed: {me.text}")

        weather = client.get(
            "/api/weather-check",
            params={"lat": 38.42, "lon": 27.14, "panel_kw": 5, "day": "today"},
            headers=headers,
        )
        _check(
            weather.status_code == 403,
            f"weather diagnostics must reject non-admin users: {weather.status_code}",
        )

        plan = client.get(f"/api/plan/{user_id}", params={"day": "tomorrow"}, headers=headers)
        _check(plan.status_code == 200, f"plan failed: {plan.status_code} {plan.text}")
        plan_body = plan.json()
        _check("chart_data" in plan_body, "plan has no chart_data")

        report = client.get(
            f"/api/report/{user_id}",
            params={"month": date.today().strftime("%Y-%m")},
            headers=headers,
        )
        _check(report.status_code == 200, f"report failed: {report.status_code} {report.text}")

    print(f"OK Wattra smoke passed: {base}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
