"""Wattra API — FastAPI application.

Endpoints map one-to-one to the mobile app screens:
  POST /api/auth/register   → Auth registration (email + password + profile)
  POST /api/auth/login      → Login → access + refresh tokens
  POST /api/auth/refresh    → Refresh access token
  GET  /api/auth/me         → Authenticated user profile
  PUT  /api/auth/me         → Update name / household profile
  PUT  /api/auth/password   → Change password

  POST /api/register        → Onboarding (legacy, backward-compatible)
  GET  /api/plan/{id}       → Today screen (fast plan, no agent)
  POST /api/assistant       → Assistant chat (Gemini agent / fallback)
  GET  /api/report/{id}     → Monthly report (counterfactual + CO2)
  GET  /api/notifications/{id} → Proactive alerts
  POST /api/feedback        → "applied / not applied"
  GET  /api/device-catalog  → Onboarding device catalog
"""

import json
import logging
import os
import sqlite3
import time
from datetime import date, timedelta

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config, db
from .agent import assistant_reply
from .agent.context import ToolContext
from .auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user_id,
    hash_password,
    require_same_user,
    verify_password,
)
from .schemas import (
    AssistantRequest,
    AssistantResponse,
    AuthLoginRequest,
    AuthRegisterRequest,
    DailyPlan,
    Feedback,
    HouseholdProfile,
    MonthlyReport,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserProfileResponse,
    WeatherCheck,
)
from .services.notifications import notifications
from .services.report import monthly_report
from .tools.production import forecast_production
from .tools.weather import get_weather

APP_VERSION = "0.2.0"

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title="Wattra API", version=APP_VERSION,
              description="Rooftop-PV energy assistant — tailored for Turkey")

# CORS origins are env-driven for production: set WATTRA_CORS_ORIGINS to a
# comma-separated allow-list (e.g. the deployed web URL). Defaults to "*" for
# local development and Expo Go.
_origins = os.getenv("WATTRA_CORS_ORIGINS", "*").strip()
_allow_origins = ["*"] if _origins == "*" else [o.strip() for o in _origins.split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_allow_origins, allow_methods=["*"],
                   allow_headers=["*"])

log = logging.getLogger("wattra.api")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """One structured log line per request (method, path, status, duration)."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    log.info("%s %s -> %s (%.0f ms)", request.method, request.url.path,
             response.status_code, duration_ms)
    return response


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    """Never leak a stack trace to the client; log it and return clean JSON.
    (HTTPException is handled by FastAPI's own handler, so 404s etc. are intact.)"""
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Sunucuda bir hata oluştu."})


# The schema is prepared at import time (works in every environment incl. TestClient)
db.init_db()


# ──────────────────────────────────────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    agent = "gemini" if config.GEMINI_API_KEY else "ollama" if config.OLLAMA_ENABLED else "fallback"
    return {"status": "ok", "version": APP_VERSION, "agent": agent}


@app.get("/api/model-versions")
def model_versions():
    """Transparency endpoint: returns every model/optimizer version in use."""
    manifest_path = os.path.join(os.path.dirname(__file__), "models", "manifest.json")
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError):
        manifest = {}
    return {
        "production_model": manifest.get("production", {}).get("version", "unknown"),
        "consumption_model": manifest.get("consumption", {}).get("version", "unknown"),
        "optimizer": config.OPTIMIZER_VERSION,
        "app_version": APP_VERSION,
        "manifest": manifest,
    }

# ──────────────────────────────────────────────────────────────────────────────
# Authentication endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/api/auth/register", response_model=TokenResponse)
def auth_register(req: AuthRegisterRequest):
    """Create a new account with e-mail + password + household profile."""
    if db.get_user_by_email(req.email):
        raise HTTPException(409, "Bu e-posta adresi zaten kayıtlı")
    try:
        user_id = db.create_auth_user(
            email=req.email,
            password_hash=hash_password(req.password),
            name=req.name,
            profile=req.profile,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Bu e-posta adresi zaten kayıtlı")
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
        user_id=user_id,
        name=req.name,
        message=f"Hoş geldin! {req.profile.panel_kw} kW'lık sistemin için hazırım.",
    )


@app.post("/api/auth/login", response_model=TokenResponse)
def auth_login(req: AuthLoginRequest):
    """Log in with e-mail + password → access + refresh tokens."""
    user = db.get_user_by_email(req.email)
    if not user or not user.get("password_hash"):
        raise HTTPException(401, "E-posta veya şifre hatalı")
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "E-posta veya şifre hatalı")
    return TokenResponse(
        access_token=create_access_token(user["id"]),
        refresh_token=create_refresh_token(user["id"]),
        user_id=user["id"],
        name=user.get("name", ""),
        message="Tekrar hoş geldin!",
    )


@app.post("/api/auth/refresh", response_model=TokenResponse)
def auth_refresh(req: RefreshRequest):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Refresh token bekleniyor")
    user_id = int(payload["sub"])
    info = db.get_user_auth_info(user_id)
    if not info:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
        user_id=user_id,
        name=info.get("name", ""),
        message="Token yenilendi",
    )


@app.get("/api/auth/me", response_model=UserProfileResponse)
def auth_me(uid: int = Depends(get_current_user_id)):
    """Return the authenticated user's full profile."""
    info = db.get_user_auth_info(uid)
    if not info:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return UserProfileResponse(
        user_id=info["id"],
        email=info.get("email", ""),
        name=info.get("name", ""),
        profile=HouseholdProfile.model_validate_json(info["profile"]),
    )


@app.put("/api/auth/me", response_model=UserProfileResponse)
def auth_update_me(req: ProfileUpdateRequest,
                   uid: int = Depends(get_current_user_id)):
    """Update the authenticated user's name, email, and/or household profile."""
    info = db.get_user_auth_info(uid)
    if not info:
        raise HTTPException(404, "Kullanıcı bulunamadı")

    if req.email is not None:
        email = req.email.lower().strip()
        if not email:
            raise HTTPException(400, "Geçersiz e-posta adresi")
        # Check if email is already used by someone else
        existing = db.get_user_by_email(email)
        if existing and existing["id"] != uid:
            raise HTTPException(409, "Bu e-posta adresi zaten kullanılıyor")
        db.update_user_email(uid, email)

    if req.name is not None:
        db.update_user_name(uid, req.name)
    if req.profile is not None:
        db.update_user(uid, req.profile)
    # Return the refreshed profile
    info = db.get_user_auth_info(uid)
    return UserProfileResponse(
        user_id=info["id"],
        email=info.get("email", ""),
        name=info.get("name", ""),
        profile=HouseholdProfile.model_validate_json(info["profile"]),
    )


@app.put("/api/auth/password")
def auth_change_password(req: PasswordChangeRequest,
                         uid: int = Depends(get_current_user_id)):
    """Change the authenticated user's password."""
    info = db.get_user_auth_info(uid)
    if not info:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    # Verify current password
    user = db.get_user_by_email(info.get("email", ""))
    if not user or not verify_password(req.current_password, user["password_hash"]):
        raise HTTPException(401, "Mevcut şifre hatalı")
    db.update_user_password(uid, hash_password(req.new_password))
    return {"status": "updated", "message": "Şifre başarıyla değiştirildi"}


# ──────────────────────────────────────────────────────────────────────────────
# Weather check (public — no auth required)
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/weather-check", response_model=WeatherCheck)
def weather_check(lat: float, lon: float, panel_kw: float = 5.0, day: str = "today"):
    if day in ("today", "bugun", "bugün"):
        target = date.today()
    elif day in ("tomorrow", "yarin", "yarın"):
        target = date.today() + timedelta(days=1)
    else:
        try:
            target = date.fromisoformat(day)
        except ValueError as err:
            raise HTTPException(400, "Geçersiz tarih") from err
    weather = get_weather(lat, lon, target)
    production = forecast_production(weather, panel_kw)
    peak_hour = max(range(24), key=lambda h: weather.irradiance_wm2[h])
    return WeatherCheck(
        date=target,
        lat=lat,
        lon=lon,
        total_irradiance_kwh_m2=round(sum(weather.irradiance_wm2) / 1000, 2),
        peak_irradiance_wm2=round(weather.irradiance_wm2[peak_hour], 1),
        peak_hour=peak_hour,
        avg_cloud_pct=round(sum(weather.cloud_pct) / 24, 1),
        min_temp_c=round(min(weather.temp_c), 1),
        max_temp_c=round(max(weather.temp_c), 1),
        production_model_version=production.model_version,
        estimated_production_kwh=production.total_kwh,
        weather_source=weather.source,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Legacy register (backward-compatible — no auth)
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/api/register", response_model=RegisterResponse)
def register(req: RegisterRequest):
    user_id = db.add_user(req.profile)
    return RegisterResponse(user_id=user_id,
                            message=f"Hoş geldin! {req.profile.panel_kw} kW'lık sistemin için hazırım.")


# ──────────────────────────────────────────────────────────────────────────────
# Protected endpoints (require Bearer token)
# ──────────────────────────────────────────────────────────────────────────────

@app.put("/api/profile/{user_id}")
def update_profile(user_id: int, profile: HouseholdProfile,
                   token_uid: int = Depends(get_current_user_id)):
    require_same_user(token_uid, user_id)
    if not db.get_user(user_id):
        raise HTTPException(404, "Kullanıcı bulunamadı")
    db.update_user(user_id, profile)
    return {"status": "updated"}


@app.get("/api/profile/{user_id}", response_model=HouseholdProfile)
def get_profile(user_id: int,
                token_uid: int = Depends(get_current_user_id)):
    require_same_user(token_uid, user_id)
    profile = db.get_user(user_id)
    if not profile:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return profile


@app.get("/api/plan/{user_id}", response_model=DailyPlan)
def daily_plan(user_id: int, day: str = "today",
               token_uid: int = Depends(get_current_user_id)):
    """Today screen: deterministic plan without hitting the LLM (fast and free).
    The assistant chat runs through the agent instead."""
    require_same_user(token_uid, user_id)
    profile = db.get_user(user_id)
    if not profile:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    context = ToolContext(user_id, profile)
    context.optimize(day)
    return context.last_plan


@app.post("/api/assistant", response_model=AssistantResponse)
def assistant(req: AssistantRequest,
              token_uid: int = Depends(get_current_user_id)):
    require_same_user(token_uid, req.user_id)
    profile = db.get_user(req.user_id)
    if not profile:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return assistant_reply(req.user_id, profile, req.message)


@app.post("/api/feedback")
def feedback(fb: Feedback,
             token_uid: int = Depends(get_current_user_id)):
    require_same_user(token_uid, fb.user_id)
    db.save_feedback(fb.user_id, fb.date, fb.item_name, fb.applied)
    return {"status": "saved"}


@app.get("/api/report/{user_id}", response_model=MonthlyReport)
def report(user_id: int, month: str | None = None,
           token_uid: int = Depends(get_current_user_id)):
    require_same_user(token_uid, user_id)
    if not db.get_user(user_id):
        raise HTTPException(404, "Kullanıcı bulunamadı")
    month = month or date.today().strftime("%Y-%m")
    return monthly_report(user_id, month)


@app.get("/api/notifications/{user_id}")
def notification_list(user_id: int,
                      token_uid: int = Depends(get_current_user_id)):
    require_same_user(token_uid, user_id)
    profile = db.get_user(user_id)
    if not profile:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return {"notifications": notifications(profile)}


@app.get("/api/device-catalog")
def device_catalog():
    path = os.path.join(os.path.dirname(__file__), "data", "devices.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)
