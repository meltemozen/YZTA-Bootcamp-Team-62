"""Wattra API — FastAPI application.

Endpoints map one-to-one to the mobile app screens:
  POST /api/register        → Onboarding
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
import time
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config, db
from .agent import assistant_reply
from .agent.context import ToolContext
from .schemas import (
    AssistantRequest,
    AssistantResponse,
    DailyPlan,
    Feedback,
    HouseholdProfile,
    MonthlyReport,
    RegisterRequest,
    RegisterResponse,
    WeatherCheck,
)
from .services.notifications import notifications
from .services.report import monthly_report
from .tools.production import forecast_production
from .tools.weather import get_weather

APP_VERSION = "0.1.0"

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


@app.get("/api/health")
def health():
    agent = "gemini" if config.GEMINI_API_KEY else "ollama" if config.OLLAMA_ENABLED else "fallback"
    return {"status": "ok", "version": APP_VERSION, "agent": agent}


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
    )


@app.post("/api/register", response_model=RegisterResponse)
def register(req: RegisterRequest):
    user_id = db.add_user(req.profile)
    return RegisterResponse(user_id=user_id,
                            message=f"Hoş geldin! {req.profile.panel_kw} kW'lık sistemin için hazırım.")


@app.put("/api/profile/{user_id}")
def update_profile(user_id: int, profile: HouseholdProfile):
    if not db.get_user(user_id):
        raise HTTPException(404, "Kullanıcı bulunamadı")
    db.update_user(user_id, profile)
    return {"status": "updated"}


@app.get("/api/profile/{user_id}", response_model=HouseholdProfile)
def get_profile(user_id: int):
    profile = db.get_user(user_id)
    if not profile:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return profile


@app.get("/api/plan/{user_id}", response_model=DailyPlan)
def daily_plan(user_id: int, day: str = "today"):
    """Today screen: deterministic plan without hitting the LLM (fast and free).
    The assistant chat runs through the agent instead."""
    profile = db.get_user(user_id)
    if not profile:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    context = ToolContext(user_id, profile)
    context.optimize(day)
    return context.last_plan


@app.post("/api/assistant", response_model=AssistantResponse)
def assistant(req: AssistantRequest):
    profile = db.get_user(req.user_id)
    if not profile:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return assistant_reply(req.user_id, profile, req.message)


@app.post("/api/feedback")
def feedback(fb: Feedback):
    db.save_feedback(fb.user_id, fb.date, fb.item_name, fb.applied)
    return {"status": "saved"}


@app.get("/api/report/{user_id}", response_model=MonthlyReport)
def report(user_id: int, month: str | None = None):
    if not db.get_user(user_id):
        raise HTTPException(404, "Kullanıcı bulunamadı")
    month = month or date.today().strftime("%Y-%m")
    return monthly_report(user_id, month)


@app.get("/api/notifications/{user_id}")
def notification_list(user_id: int):
    profile = db.get_user(user_id)
    if not profile:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return {"notifications": notifications(profile)}


@app.get("/api/device-catalog")
def device_catalog():
    path = os.path.join(os.path.dirname(__file__), "data", "devices.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)
