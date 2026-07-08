"""Agent-layer evaluation suite (fallback path — deterministic, no key/network).

These are behavioural "evals": given a user message, assert the agent
orchestrates the right tools, honours constraints, persists preferences, and —
critically — produces a reply whose numbers are all grounded in the plan.
"""

import os
import tempfile

os.environ["WATTRA_DB"] = os.path.join(tempfile.mkdtemp(), "agent_test.db")
os.environ.pop("GEMINI_API_KEY", None)

from app import config  # noqa: E402

config.GEMINI_API_KEY = ""
config.DB_PATH = os.environ["WATTRA_DB"]

from app import db  # noqa: E402
from app.agent import assistant_reply, orchestrator  # noqa: E402
from app.agent.grounding import ungrounded_numbers  # noqa: E402
from app.schemas import Device, HouseholdProfile  # noqa: E402


def _profile() -> HouseholdProfile:
    return HouseholdProfile(
        user_type="home", panel_kw=5.0, monthly_bill_kwh=300, tariff_type="single",
        devices=[Device(name="Çamaşır makinesi", kwh=1.0, duration_h=2,
                        earliest=8, latest=23)],
    )


def _new_user() -> int:
    db.init_db()
    return db.add_user(_profile())


def test_fallback_orchestrates_multiple_tools():
    uid = _new_user()
    r = assistant_reply(uid, db.get_user(uid), "yarın için plan yap")
    assert r.agent_mode == "fallback"
    assert r.plan is not None and r.plan.items, "a plan with items must be produced"
    # Real orchestration evidence: the weather→...→optimize chain was walked.
    assert any("get_weather" in c for c in r.tool_calls)
    assert any("optimize" in c for c in r.tool_calls)


def test_objection_persists_preference_and_constrains_plan():
    uid = _new_user()
    r = assistant_reply(uid, db.get_user(uid), "22'den sonra çamaşır çalıştırma")
    assert any("write_memory" in c for c in r.tool_calls), "objection must be remembered"
    assert db.preferences(uid), "preference must be persisted to memory"
    # The device must not be scheduled into the blocked late-night hours.
    device = next((i for i in r.plan.items if i.type == "device"), None)
    if device is not None:
        run_hours = {(device.start_h + i) % 24 for i in range(2)}
        assert not (run_hours & {22, 23, 0, 1, 2, 3, 4, 5, 6, 7})


def test_reply_numbers_are_grounded():
    """Honesty guard: every TL/CO2 figure in the reply must trace to the plan."""
    uid = _new_user()
    r = assistant_reply(uid, db.get_user(uid), "bugün plan")
    assert r.plan is not None
    bad = ungrounded_numbers(r.reply, r.plan)
    assert bad == [], f"reply contains ungrounded numbers: {bad}\nreply: {r.reply}"


def test_grounding_catches_a_hallucinated_figure():
    uid = _new_user()
    r = assistant_reply(uid, db.get_user(uid), "bugün plan")
    tampered = r.reply + " Ayrıca bu ay 999 TL daha kazanacaksın."
    assert 999.0 in ungrounded_numbers(tampered, r.plan)


def test_gemini_ungrounded_reply_falls_back(monkeypatch):
    uid = _new_user()

    def fake_gemini_loop(context, message):
        context.optimize("today")
        return "Bugün 999 TL tasarruf edeceksin."

    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(orchestrator, "_gemini_loop", fake_gemini_loop)

    r = orchestrator.assistant_reply(uid, db.get_user(uid), "bugün plan")

    assert r.agent_mode == "fallback"
    assert "999" not in r.reply
    assert ungrounded_numbers(r.reply, r.plan) == []


def test_transparency_tool_calls_exposed():
    uid = _new_user()
    r = assistant_reply(uid, db.get_user(uid), "çamaşırı ne zaman atayım")
    assert r.tool_calls, "tool call chain must be exposed for transparency"
