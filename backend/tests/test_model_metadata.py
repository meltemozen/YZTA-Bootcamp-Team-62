"""Model version/metadata transparency tests.

Covers the gap found while auditing "which model version produced this
number": production/consumption model_version was already surfaced end-to-end,
but trained_at (when the artifact was built) and an optimizer version tag were
missing entirely, and models/manifest.json's documented consumption version
had drifted from what's actually deployed. See docs/SPRINTS.md TDB-4.
"""

import json
import os
from datetime import date, timedelta

from app.schemas import Device, HouseholdProfile, Weather
from app.tools import consumption, production
from app.tools.optimize import optimize
from app.tools.tariff import get_tariff

DAY = date.today() + timedelta(days=2)
_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "models")


def _weather() -> Weather:
    irradiance = [0.0] * 24
    for h in range(6, 20):
        irradiance[h] = 900 * max(0.0, 1 - abs(h - 13) / 7)
    return Weather(date=DAY, irradiance_wm2=irradiance, temp_c=[28.0] * 24, cloud_pct=[10.0] * 24)


def _profile() -> HouseholdProfile:
    return HouseholdProfile(
        user_type="home", panel_kw=5.0, monthly_bill_kwh=300, tariff_type="single",
        devices=[Device(name="Çamaşır makinesi", kwh=1.0, duration_h=2, earliest=8, latest=23)],
    )


# --- Real artifacts carry trained_at (the JSON metadata sidecar is read
# regardless of whether the LightGBM booster itself loads) ---

def test_production_forecast_carries_trained_at():
    forecast = production.forecast_production(_weather(), panel_kw=5.0)
    assert forecast.trained_at == "2026-07-15"


def test_consumption_forecast_carries_trained_at():
    forecast = consumption.forecast_consumption(_profile(), DAY)
    assert forecast.trained_at == "2026-07-13"


# --- Hardcoded fallbacks (no artifact file) honestly report no training date ---

def test_production_physical_fallback_has_no_trained_at(monkeypatch):
    monkeypatch.setattr(production, "_MODEL_PATH", "/nonexistent/production.json")
    model = production._load_model.__wrapped__()
    assert model["model_version"] == "v0-physical"
    assert model["trained_at"] is None


def test_consumption_profile_fallback_has_no_trained_at(monkeypatch):
    monkeypatch.setattr(consumption, "_MODEL_PATH", "/nonexistent/consumption.json")
    model = consumption._load_model.__wrapped__()
    assert model["model_version"] == "v0-profile"
    assert model["trained_at"] is None


# --- Optimizer has no trained artifact but still carries a manually-bumped
# version tag, both at the top level and inside chart_data.models ---

def test_daily_plan_carries_optimizer_version_and_model_dates():
    weather = _weather()
    prod = production.forecast_production(weather, panel_kw=5.0)
    profile = _profile()
    cons = consumption.forecast_consumption(profile, DAY)
    tariff = get_tariff(DAY, profile.user_type, profile.tariff_type,
                        monthly_kwh=profile.monthly_bill_kwh)

    plan = optimize(prod, cons, tariff, profile)

    assert plan.optimizer_version == "v1-greedy-coordinate-descent"
    assert plan.chart_data["models"]["production_trained_at"] == prod.trained_at
    assert plan.chart_data["models"]["consumption_trained_at"] == cons.trained_at


# --- Regression guard for the exact staleness bug this audit found:
# manifest.json must describe what's actually deployed. ---

def test_manifest_matches_actual_model_artifacts():
    with open(os.path.join(_MODELS_DIR, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    with open(os.path.join(_MODELS_DIR, "production_v1.json"), encoding="utf-8") as f:
        production_artifact = json.load(f)
    with open(os.path.join(_MODELS_DIR, "consumption_v1.json"), encoding="utf-8") as f:
        consumption_artifact = json.load(f)

    assert manifest["production"]["active_version"] == production_artifact["model_version"]
    assert manifest["production"]["trained_at"] == production_artifact["trained_at"]
    assert manifest["consumption"]["active_version"] == consumption_artifact["model_version"]
    assert manifest["consumption"]["trained_at"] == consumption_artifact["trained_at"]
    assert "optimizer" in manifest
