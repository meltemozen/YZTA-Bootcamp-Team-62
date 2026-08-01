"""API smoke tests — auth-register → plan → assistant (fallback) → report flow.

Requires no Gemini key; the weather tool falls back to a synthetic profile when
offline, so the flow works in every environment.
"""

import os
import tempfile

os.environ["WATTRA_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.pop("GEMINI_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402

config.GEMINI_API_KEY = ""
config.DB_PATH = os.environ["WATTRA_DB"]

from app.main import app  # noqa: E402

client = TestClient(app)

PROFILE = {
    "user_type": "home", "city": "İzmir", "lat": 38.42, "lon": 27.14,
    "panel_kw": 5.0, "battery_kwh": 0, "battery_power_kw": 0,
    "monthly_bill_kwh": 300, "tariff_type": "three_zone",
    "devices": [{"name": "Çamaşır makinesi", "kwh": 1.0, "duration_h": 2,
                 "earliest": 8, "latest": 23}],
}

# Counter to generate unique emails for each test
_email_counter = 0


def _auth_register():
    """Register via the new auth endpoint and return (user_id, headers)."""
    global _email_counter
    _email_counter += 1
    email = f"apitest{_email_counter}@wattra.dev"
    resp = client.post("/api/auth/register", json={
        "email": email, "password": "testpass123", "name": "Test", "profile": PROFILE,
    })
    assert resp.status_code == 200
    body = resp.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    return body["user_id"], headers


def _legacy_register() -> int:
    """Register via the legacy (no-auth) endpoint for backward-compat test."""
    resp = client.post("/api/register", json={"profile": PROFILE})
    assert resp.status_code == 200
    return resp.json()["user_id"]


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["agent"] == "fallback"


def test_weather_check_uses_location_and_model():
    resp = client.get("/api/weather-check?lat=38.42&lon=27.14&panel_kw=5&day=tomorrow")
    assert resp.status_code == 200
    body = resp.json()
    assert body["estimated_production_kwh"] >= 0
    assert 0 <= body["peak_hour"] <= 23
    assert body["production_model_version"].startswith("v1-")


def test_legacy_register():
    """The old register endpoint still works (backward compatibility)."""
    uid = _legacy_register()
    assert uid > 0


def test_end_to_end_flow():
    uid, headers = _auth_register()

    # Daily plan
    plan = client.get(f"/api/plan/{uid}?day=tomorrow", headers=headers)
    assert plan.status_code == 200
    body = plan.json()
    assert body["items"], "Plan must contain at least one item"
    assert body["total_saving_tl_max"] >= body["total_saving_tl_min"]
    assert body["chart_data"]["models"]["production"].startswith("v")
    assert body["chart_data"]["models"]["consumption"].startswith("v")

    # Assistant (reasoned Turkish reply in fallback mode)
    resp = client.post("/api/assistant", json={"user_id": uid,
                                               "message": "yarın için plan yapar mısın"},
                       headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_mode"] == "fallback"
    assert "TL" in body["reply"]
    assert body["tool_calls"], "Transparency: the list of called tools must be non-empty"

    # Objection → written to memory, plan changes
    objection = client.post("/api/assistant", json={"user_id": uid,
                                                    "message": "öğlen 12den önce evde yokum"},
                            headers=headers)
    assert objection.status_code == 200
    assert any("write_memory" in c for c in objection.json()["tool_calls"])

    # Feedback + report
    date_ = plan.json()["date"]
    fb = client.post("/api/feedback", json={
        "user_id": uid, "date": date_,
        "item_name": "Çamaşır makinesi", "applied": True}, headers=headers)
    assert fb.status_code == 200

    month = date_[:7]
    report = client.get(f"/api/report/{uid}?month={month}", headers=headers)
    assert report.status_code == 200
    assert report.json()["applied_count"] >= 1

    # Proactive notifications
    notif = client.get(f"/api/notifications/{uid}", headers=headers)
    assert notif.status_code == 200
    assert isinstance(notif.json()["notifications"], list)


def test_device_catalog():
    resp = client.get("/api/device-catalog")
    assert resp.status_code == 200
    assert len(resp.json()["devices"]) >= 5


def test_unauthenticated_plan_returns_401():
    """Protected endpoints require a Bearer token."""
    resp = client.get("/api/plan/1?day=tomorrow")
    assert resp.status_code == 401
