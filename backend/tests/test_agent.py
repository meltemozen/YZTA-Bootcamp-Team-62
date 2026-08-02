"""Assistant provider, grounding and preference persistence tests."""

import os
import tempfile
from datetime import date

import pytest

os.environ["WATTRA_DB"] = os.path.join(tempfile.mkdtemp(), "agent_test.db")

from app import config, db  # noqa: E402
from app.agent import orchestrator  # noqa: E402
from app.agent.grounding import (  # noqa: E402
    ungrounded_dates,
    ungrounded_entities,
    ungrounded_numbers,
)
from app.schemas import CustomTariff, DailyPlan, Device, HouseholdProfile  # noqa: E402

config.DB_PATH = os.environ["WATTRA_DB"]


def _profile() -> HouseholdProfile:
    return HouseholdProfile(
        user_type="home",
        panel_kw=5.0,
        monthly_bill_kwh=300,
        tariff_type="single",
        custom_tariff=CustomTariff(single=4.5, sell=0),
        devices=[Device(name="Çamaşır makinesi", kwh=1.0, duration_h=2,
                        earliest=8, latest=23)],
    )


def _new_user() -> int:
    db.init_db()
    return db.add_user(_profile())


def test_assistant_requires_a_real_provider(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "OLLAMA_ENABLED", False)
    with pytest.raises(orchestrator.AssistantUnavailableError):
        orchestrator.assistant_reply(_new_user(), _profile(), "Bugünkü planım nedir?")


def test_gemini_response_is_returned_without_provider_metadata(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(config, "OLLAMA_ENABLED", False)
    monkeypatch.setattr(orchestrator, "_gemini_loop", lambda context, message: "Planın hazır.")

    response = orchestrator.assistant_reply(_new_user(), _profile(), "Planımı açıkla")

    assert response.reply == "Planın hazır."
    assert response.model_dump() == {"reply": "Planın hazır.", "plan": None}


def test_ollama_is_used_when_explicitly_enabled(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(orchestrator, "ollama_loop",
                        lambda context, message, **kwargs: "Yerel asistan yanıtı.")

    response = orchestrator.assistant_reply(_new_user(), _profile(), "Planımı açıkla")
    assert response.reply == "Yerel asistan yanıtı."


def test_invalid_model_answer_is_rejected(monkeypatch):
    context = orchestrator.ToolContext(_new_user(), _profile())
    context.last_plan = DailyPlan(
        date=date.today(), items=[], total_saving_tl_min=0,
        total_saving_tl_max=0, co2_saved_kg=0, self_consumption_ratio=0,
    )
    with pytest.raises(orchestrator.AssistantUnavailableError):
        orchestrator._safe_response(context, "999 TL tasarruf edeceksin.", "plan", "gemini")


def test_preference_backstop_persists_user_constraint(monkeypatch):
    uid = _new_user()
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(config, "OLLAMA_ENABLED", False)
    monkeypatch.setattr(orchestrator, "_gemini_loop", lambda context, message: "Tercihin kaydedildi.")

    orchestrator.assistant_reply(uid, _profile(), "22'den sonra çalıştırma")

    assert db.preferences(uid)[0]["text"] == "22'den sonra çalıştırma"


def test_grounding_detects_unrelated_numbers_entities_and_dates():
    plan = DailyPlan(
        date=date(2026, 8, 2), items=[], total_saving_tl_min=0,
        total_saving_tl_max=0, co2_saved_kg=0, self_consumption_ratio=0,
    )
    assert 999.0 in ungrounded_numbers("999 TL tasarruf", plan)
    assert "batarya" in ungrounded_entities("Bataryanı şarj et", plan)
    assert ungrounded_dates("Pazartesi için planladım", plan)


def test_llm_arguments_are_coerced_to_tool_signature():
    def tool(date=None, blocked_hours=None):
        return date, blocked_hours

    args = orchestrator._clean_args(tool, {"date": "today", "blocked_hours": ["1", 2], "extra": 1})
    assert args == {"date": "today", "blocked_hours": [2]}
