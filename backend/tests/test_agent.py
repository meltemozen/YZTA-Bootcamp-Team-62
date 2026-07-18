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
from app.agent.context import ToolContext  # noqa: E402
from app.agent.grounding import ungrounded_numbers  # noqa: E402
from app.agent.local_llm import ollama_loop  # noqa: E402
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


def test_ollama_provider_can_orchestrate_with_grounding(monkeypatch):
    uid = _new_user()

    def fake_ollama_loop(context, message, **kwargs):
        context.get_weather("today")
        context.forecast_production("today")
        context.forecast_consumption("today")
        context.get_tariff("today")
        summary = context.optimize("today")
        low, high = summary["total_saving_tl"]
        return f"Yerel model planı kurdu: yaklaşık {low:.0f}-{high:.0f} TL tasarruf."

    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(orchestrator, "ollama_loop", fake_ollama_loop)

    r = orchestrator.assistant_reply(uid, db.get_user(uid), "bugün plan")

    assert r.agent_mode == "ollama"
    assert r.plan is not None
    assert any("optimize" in c for c in r.tool_calls)
    assert ungrounded_numbers(r.reply, r.plan) == []


def test_ollama_loop_executes_tool_calls(monkeypatch):
    uid = _new_user()
    context = ToolContext(uid, db.get_user(uid))
    responses = [
        {"message": {"role": "assistant", "tool_calls": [
            {"function": {"name": "optimize", "arguments": {"date": "today"}}}
        ]}},
        {"message": {"role": "assistant", "content": "Yerel model planı kurdu; kartlara bakabilirsin."}},
    ]

    class FakeResponse:
        def __init__(self, body):
            self.body = body

        def raise_for_status(self):
            return None

        def json(self):
            return self.body

    class FakeClient:
        def __init__(self, *args, **kwargs):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return FakeResponse(responses.pop(0))

    monkeypatch.setattr("app.agent.local_llm.httpx.Client", FakeClient)

    text = ollama_loop(
        context,
        "bugün plan",
        system_prompt=orchestrator.SYSTEM_PROMPT,
        tool_definitions=orchestrator.TOOL_DEFINITIONS,
        clean_args=orchestrator._clean_args,
        max_steps=orchestrator.MAX_STEPS,
    )

    assert "Yerel model" in text
    assert context.last_plan is not None
    assert any("optimize" in c for c in context.calls)


def test_transparency_tool_calls_exposed():
    uid = _new_user()
    r = assistant_reply(uid, db.get_user(uid), "çamaşırı ne zaman atayım")
    assert r.tool_calls, "tool call chain must be exposed for transparency"


def test_backstop_persists_preference_when_llm_skips_write(monkeypatch):
    """S2-4 finding: live Gemini answered "not aldım" to a preference without
    calling write_memory — the preference silently vanished. The code-level
    backstop must persist it anyway (and expose the call transparently)."""
    uid = _new_user()

    def lazy_gemini_loop(context, message):
        return "Anladım, haftaya salı dışarıda olacağını not aldım. 😊"

    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(orchestrator, "_gemini_loop", lazy_gemini_loop)

    r = orchestrator.assistant_reply(uid, db.get_user(uid),
                                     "haftaya salı yine dışarıdayım, plana dikkat et")

    assert any("write_memory" in c for c in r.tool_calls), "backstop must write"
    prefs = db.preferences(uid)
    assert len(prefs) == 1 and "dışarıdayım" in prefs[0]["text"]


def test_backstop_does_not_duplicate_llm_write(monkeypatch):
    uid = _new_user()

    def dutiful_gemini_loop(context, message):
        context.write_memory("Salı öğlen evde yok.")
        return "Kaydettim, salı öğlenleri plana katmayacağım."

    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(orchestrator, "_gemini_loop", dutiful_gemini_loop)

    orchestrator.assistant_reply(uid, db.get_user(uid), "salı öğlen evde yokum")

    assert len(db.preferences(uid)) == 1, "LLM already wrote; backstop must not duplicate"


def test_preference_triggers_semantic_search_and_recall():
    """S2-5: a new preference first searches similar past ones; a genuinely
    similar preference is surfaced back to the user in the reply."""
    uid = _new_user()
    assistant_reply(uid, db.get_user(uid), "salı öğlen evde yokum")
    r = assistant_reply(uid, db.get_user(uid), "salı öğlen evde olmuyorum")
    assert any("search_preferences" in c for c in r.tool_calls), \
        "preference must trigger a similarity search"
    assert "salı öğlen evde yokum" in r.reply, "similar past preference must be recalled"
