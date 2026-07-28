"""Authentication tests — register, login, token refresh, password change,
and access control.

Requires no Gemini key; runs fully offline.
"""

import os
import tempfile

os.environ["WATTRA_DB"] = os.path.join(tempfile.mkdtemp(), "test_auth.db")
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


def _auth_register(email="test@wattra.dev", password="test1234", name="Test Kullanıcı"):
    return client.post("/api/auth/register", json={
        "email": email, "password": password, "name": name, "profile": PROFILE,
    })


def _auth_login(email="test@wattra.dev", password="test1234"):
    return client.post("/api/auth/login", json={
        "email": email, "password": password,
    })


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


# --- Registration ---

def test_register_success():
    resp = _auth_register(email="reg@wattra.dev")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] > 0
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["name"] == "Test Kullanıcı"
    assert "kW" in body["message"]


def test_register_duplicate_email():
    email = "dup@wattra.dev"
    resp1 = _auth_register(email=email)
    assert resp1.status_code == 200
    resp2 = _auth_register(email=email)
    assert resp2.status_code == 409


def test_register_short_password():
    resp = _auth_register(email="short@wattra.dev", password="123")
    assert resp.status_code == 422  # validation error


# --- Login ---

def test_login_success():
    _auth_register(email="login@wattra.dev", password="securepass")
    resp = _auth_login(email="login@wattra.dev", password="securepass")
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert "hoş geldin" in body["message"].lower()


def test_login_wrong_password():
    _auth_register(email="wrong@wattra.dev", password="correct")
    resp = _auth_login(email="wrong@wattra.dev", password="incorrect")
    assert resp.status_code == 401


def test_login_nonexistent_email():
    resp = _auth_login(email="ghost@wattra.dev", password="anything")
    assert resp.status_code == 401


# --- Token refresh ---

def test_refresh_token():
    reg = _auth_register(email="refresh@wattra.dev")
    refresh_tok = reg.json()["refresh_token"]
    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_tok})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_refresh_with_access_token_fails():
    reg = _auth_register(email="badrefresh@wattra.dev")
    access_tok = reg.json()["access_token"]
    resp = client.post("/api/auth/refresh", json={"refresh_token": access_tok})
    assert resp.status_code == 401


# --- Protected profile (GET /api/auth/me) ---

def test_auth_me():
    reg = _auth_register(email="me@wattra.dev")
    token = reg.json()["access_token"]
    resp = client.get("/api/auth/me", headers=_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@wattra.dev"
    assert body["name"] == "Test Kullanıcı"
    assert body["profile"]["panel_kw"] == 5.0


def test_auth_me_no_token():
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_auth_me_invalid_token():
    resp = client.get("/api/auth/me", headers=_headers("fake.invalid.token"))
    assert resp.status_code == 401


# --- Profile update (PUT /api/auth/me) ---

def test_update_profile():
    reg = _auth_register(email="update@wattra.dev")
    token = reg.json()["access_token"]
    resp = client.put("/api/auth/me", headers=_headers(token), json={
        "name": "Yeni İsim",
        "profile": {**PROFILE, "panel_kw": 8.0},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Yeni İsim"
    assert body["profile"]["panel_kw"] == 8.0


# --- Password change ---

def test_change_password():
    _auth_register(email="pwchange@wattra.dev", password="oldpass123")
    login = _auth_login(email="pwchange@wattra.dev", password="oldpass123")
    token = login.json()["access_token"]

    # Change password
    resp = client.put("/api/auth/password", headers=_headers(token), json={
        "current_password": "oldpass123",
        "new_password": "newpass456",
    })
    assert resp.status_code == 200

    # Old password should fail
    resp2 = _auth_login(email="pwchange@wattra.dev", password="oldpass123")
    assert resp2.status_code == 401

    # New password should work
    resp3 = _auth_login(email="pwchange@wattra.dev", password="newpass456")
    assert resp3.status_code == 200


def test_change_password_wrong_current():
    _auth_register(email="pwwrong@wattra.dev", password="mypass")
    login = _auth_login(email="pwwrong@wattra.dev", password="mypass")
    token = login.json()["access_token"]
    resp = client.put("/api/auth/password", headers=_headers(token), json={
        "current_password": "wrongpass",
        "new_password": "newpass123",
    })
    assert resp.status_code == 401


# --- Access control (user cannot access another user's data) ---

def test_cross_user_plan_access_denied():
    reg1 = _auth_register(email="user1@wattra.dev")
    reg2 = _auth_register(email="user2@wattra.dev")
    token1 = reg1.json()["access_token"]
    uid2 = reg2.json()["user_id"]

    # User 1 trying to access User 2's plan
    resp = client.get(f"/api/plan/{uid2}?day=tomorrow", headers=_headers(token1))
    assert resp.status_code == 403


def test_cross_user_profile_access_denied():
    reg1 = _auth_register(email="xuser1@wattra.dev")
    reg2 = _auth_register(email="xuser2@wattra.dev")
    token1 = reg1.json()["access_token"]
    uid2 = reg2.json()["user_id"]

    resp = client.get(f"/api/profile/{uid2}", headers=_headers(token1))
    assert resp.status_code == 403
