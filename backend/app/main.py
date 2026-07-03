"""Voltaic API — FastAPI application.

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
import os
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config, db
from .agent import assistant_reply
from .agent.context import ToolContext
from .schemas import (AssistantRequest, AssistantResponse, DailyPlan, Feedback,
                      HouseholdProfile, MonthlyReport, RegisterRequest, RegisterResponse)
from .services.notifications import notifications
from .services.report import monthly_report

app = FastAPI(title="Voltaic API", version="0.1.0",
              description="Rooftop-PV energy assistant — tailored for Turkey")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


# The schema is prepared at import time (works in every environment incl. TestClient)
db.init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "agent": "gemini" if config.GEMINI_API_KEY else "fallback"}


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
