"""API smoke tests for authenticated planning and reporting."""

import os
import tempfile

os.environ["WATTRA_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.pop("GEMINI_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.schemas import Weather  # noqa: E402

config.GEMINI_API_KEY = ""
config.DB_PATH = os.environ["WATTRA_DB"]

from app.main import app  # noqa: E402

client = TestClient(app)

PROFILE = {
    "user_type": "home", "city": "İzmir", "lat": 38.42, "lon": 27.14,
    "panel_kw": 5.0, "battery_kwh": 0, "battery_power_kw": 0,
    "monthly_bill_kwh": 300, "tariff_type": "three_zone",
    "custom_tariff": {"day": 5.5, "peak": 8.0, "night": 3.5, "sell": 0},
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


def _live_weather(_lat, _lon, target):
    irradiance = [0.0] * 24
    for hour in range(6, 20):
        irradiance[hour] = 800 * max(0, 1 - abs(hour - 13) / 7)
    return Weather(
        date=target,
        irradiance_wm2=irradiance,
        temp_c=[25.0] * 24,
        cloud_pct=[15.0] * 24,
        source="live",
    )


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "ok", "version": "0.2.0"}


def test_weather_check_uses_location_and_model(monkeypatch):
    import app.main as main_module
    from app import db

    monkeypatch.setattr(main_module, "get_weather", _live_weather)
    uid, headers = _auth_register()
    db.set_user_admin(uid)
    resp = client.get(
        "/api/weather-check?lat=38.42&lon=27.14&panel_kw=5&day=tomorrow",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["estimated_production_kwh"] >= 0
    assert 0 <= body["peak_hour"] <= 23
    assert body["production_model_version"].startswith("v1-")


def test_location_resolve_is_authenticated_and_returns_coordinates(monkeypatch):
    import app.main as main_module

    denied = client.get("/api/locations/resolve?province=Ankara&district=Çankaya")
    assert denied.status_code == 401

    _uid, headers = _auth_register()
    monkeypatch.setattr(main_module, "resolve_location", lambda province, district: {
        "province": province,
        "district": district,
        "label": f"{district}, {province}",
        "lat": 39.9179,
        "lon": 32.86268,
        "source": "openstreetmap",
    })
    response = client.get(
        "/api/locations/resolve?province=Ankara&district=Çankaya",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["label"] == "Çankaya, Ankara"
    assert response.json()["lat"] == 39.9179


def test_legacy_register_is_disabled():
    resp = client.post("/api/register", json={"profile": PROFILE})
    assert resp.status_code == 404


def test_end_to_end_flow(monkeypatch):
    import importlib
    context_module = importlib.import_module("app.agent.context")
    notifications_module = importlib.import_module("app.services.notifications")
    monkeypatch.setattr(context_module, "get_weather", _live_weather)
    monkeypatch.setattr(notifications_module, "get_weather", _live_weather)
    uid, headers = _auth_register()

    # Daily plan
    plan = client.get(f"/api/plan/{uid}?day=tomorrow", headers=headers)
    assert plan.status_code == 200
    body = plan.json()
    assert body["items"], "Plan must contain at least one item"
    assert body["total_saving_tl_max"] >= body["total_saving_tl_min"]
    assert body["chart_data"]["models"]["production"].startswith("v")
    assert body["chart_data"]["models"]["consumption"].startswith("v")

    # The costly local assistant is restricted to admin accounts.
    resp = client.post("/api/assistant", json={"user_id": uid,
                                               "message": "yarın için plan yapar mısın"},
                       headers=headers)
    assert resp.status_code == 403

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
    alerts = notif.json()["notifications"]
    assert isinstance(alerts, list)
    daily_alert = next(alert for alert in alerts if alert["type"] == "daily_plan")
    first_device = next(item for item in body["items"] if item["type"] == "device")
    assert f"{first_device['start_h']:02d}:00" in daily_alert["text"]


def test_plan_uses_saved_system_location(monkeypatch):
    import importlib
    context_module = importlib.import_module("app.agent.context")
    calls = []

    def weather_at_saved_location(lat, lon, target):
        calls.append((lat, lon))
        return _live_weather(lat, lon, target)

    monkeypatch.setattr(context_module, "get_weather", weather_at_saved_location)
    uid, headers = _auth_register()
    updated = {**PROFILE, "city": "Ankara", "lat": 39.9334, "lon": 32.8597}

    saved = client.put(f"/api/profile/{uid}", json=updated, headers=headers)
    plan = client.get(f"/api/plan/{uid}?day=tomorrow", headers=headers)

    assert saved.status_code == 200
    assert plan.status_code == 200
    assert calls
    assert calls[0] == (39.9334, 32.8597)


def test_device_catalog():
    resp = client.get("/api/device-catalog")
    assert resp.status_code == 200
    assert len(resp.json()["devices"]) >= 5


def test_unauthenticated_plan_returns_401():
    """Protected endpoints require a Bearer token."""
    resp = client.get("/api/plan/1?day=tomorrow")
    assert resp.status_code == 401


def test_assistant_is_admin_only(monkeypatch):
    import app.main as main_module
    from app import db

    uid, headers = _auth_register()
    denied = client.post(
        "/api/assistant",
        headers=headers,
        json={"user_id": uid, "message": "Yarın için planım nedir?"},
    )
    assert denied.status_code == 403

    db.set_user_admin(uid)
    monkeypatch.setattr(
        main_module,
        "assistant_reply",
        lambda _uid, _profile, _message: {"reply": "Plan hazır.", "plan": None},
    )
    allowed = client.post(
        "/api/assistant",
        headers=headers,
        json={"user_id": uid, "message": "Yarın için planım nedir?"},
    )
    assert allowed.status_code == 200
