"""Gemini function-calling orchestrator.

The code embodiment of a "real agent": Gemini decides ITSELF which tool to call
and when (no hand-wired pipeline), reads memory, and on a user objection writes
the preference to memory and re-plans.

If GEMINI_API_KEY is missing or a call fails, fallback.build_plan takes over —
the product never goes silent, and the response is honestly marked
agent_mode='fallback'.

The SYSTEM_PROMPT and tool descriptions are intentionally Turkish: they steer
the Turkish-speaking assistant (product behaviour), while the code identifiers
around them are English.
"""

import inspect
import logging

from .. import config
from ..schemas import AssistantResponse, HouseholdProfile
from . import fallback
from .context import ToolContext
from .grounding import ungrounded_numbers

log = logging.getLogger(__name__)


def _clean_args(tool, raw: dict) -> dict:
    """Defensive coercion of LLM-supplied tool args before execution:
    drop unknown keys, and clamp blocked_hours to valid 0–23 integers."""
    accepted = set(inspect.signature(tool).parameters)
    args = {k: v for k, v in raw.items() if k in accepted}
    if isinstance(args.get("blocked_hours"), list):
        args["blocked_hours"] = sorted(
            {int(h) % 24 for h in args["blocked_hours"] if isinstance(h, int | float)})
    return args

SYSTEM_PROMPT = """Sen Wattra'sin: Türkiye'deki çatı güneş paneli (çatı-GES) sahibi ev ve
küçük işletmelere enerji kararı veren kişisel asistan. Sade, samimi Türkçe konuşursun;
teknik jargon kullanmazsın.

GÖREVİN: Kullanıcının hedefine ulaşmak için elindeki araçları KENDİ kararınla, gereken
sırayla çağır; sonuçları birleştirip gerekçeli tek bir öneri metni üret.

KURALLAR:
1. Plan istenince önce read_memory ile tercihleri kontrol et; plana aykırı tercih varsa
   optimize'ı blocked_hours ile çağır (örn. "22'den sonra çamaşır istemiyor" → 22,23,0..7).
2. Tasarrufu HER ZAMAN aralık olarak söyle ("yaklaşık 12-18 TL"); kesin rakam verme,
   çünkü tüketim tahmini fatura kalibrasyonuna dayanır.
3. Önerinin NEDENİNİ tek cümleyle açıkla: güneş bol / puant pahalı / gece ucuz /
   saatlik mahsuplaşmada satış alıştan ~%30 ucuz olduğu için üretimi o saat içinde
   evde tüketmek kârlı.
4. Kullanıcı bir alışkanlık, kısıt veya itiraz söylerse (örn. "salı öğlen evde yokum",
   "haftaya dışarıdayım") bunu MUTLAKA write_memory aracıyla kaydet. Aracı çağırmadan
   ASLA "not aldım / dikkate alacağım" deme — kaydedilmeyen söz kullanıcıyı yanıltır.
   Sıra: önce search_preferences ile benzer eski tercihlere bak (çelişki varsa nazikçe
   sor), sonra write_memory, plan gerekiyorsa optimize'ı yeni kısıtla tekrar çağır.
5. Saat dilimleri (üç zamanlı tarife): gündüz 06-17, puant 17-22 (en pahalı), gece 22-06 (en ucuz).
   Mevzuat bilgin: mahsuplaşma 1 Mayıs 2026'dan beri SAATLİKTİR; mesken tek zamanlı
   tarife kademelidir (240 kWh/ay üstü daha pahalı); mesken çatı GES sınırı 10 kW.
6. TL tasarrufun yanında ÇEVRESEL faydayı da an: optimize çıktısındaki co2_kg ve
   env.car_km değerlerini kullan ("2.9 kg CO₂ — 17 km araba yolculuğuna denk").
7. Cevabın kısa olsun: en fazla 4-5 cümle + gerekiyorsa saat listesi. Emoji en fazla bir tane.
8. Bilmediğin şeyi uydurma; araç çıktısında olmayan sayı söyleme."""

TOOL_DEFINITIONS = [
    {"name": "get_weather",
     "description": "Bir günün saatlik hava ve güneş ışınımı özetini getirir (Open-Meteo canlı).",
     "parameters": {"type": "object", "properties": {
         "date": {"type": "string", "description": "'today', 'tomorrow' veya YYYY-MM-DD"}}}},
    {"name": "forecast_production",
     "description": "Kullanıcının paneli için bir günün saatlik güneş üretim tahminini hesaplar.",
     "parameters": {"type": "object", "properties": {
         "date": {"type": "string", "description": "'today', 'tomorrow' veya YYYY-MM-DD"}}}},
    {"name": "forecast_consumption",
     "description": "Hanenin/işyerinin baz elektrik tüketim tahminini getirir.",
     "parameters": {"type": "object", "properties": {
         "date": {"type": "string"}}}},
    {"name": "get_tariff",
     "description": "Elektrik tarifesini ve mahsuplaşma (şebekeye satış) fiyatını getirir.",
     "parameters": {"type": "object", "properties": {
         "date": {"type": "string"}}}},
    {"name": "optimize",
     "description": "Cihaz ve batarya için en ucuz günlük planı kurar. Kullanıcının istemediği "
                    "saatler varsa blocked_hours ver.",
     "parameters": {"type": "object", "properties": {
         "date": {"type": "string"},
         "blocked_hours": {"type": "array", "items": {"type": "integer"},
                           "description": "Cihaz çalıştırılmayacak saatler (0-23)"}}}},
    {"name": "read_memory",
     "description": "Kullanıcının kayıtlı tercih ve alışkanlıklarını getirir.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "search_preferences",
     "description": "Kullanıcının geçmiş tercihleri içinde ANLAMCA benzer olanları bulur "
                    "(semantik arama). Yeni bir tercih/itiraz geldiğinde ya da plana etki "
                    "edebilecek eski alışkanlıkları hatırlamak için kullan.",
     "parameters": {"type": "object", "properties": {
         "query": {"type": "string", "description": "Aranacak tercih/konu (serbest metin)"}},
         "required": ["query"]}},
    {"name": "write_memory",
     "description": "Kullanıcının söylediği kalıcı tercih/alışkanlığı hafızaya yazar. "
                    "Kullanıcı bir tercih, kısıt veya itiraz bildirdiğinde HER SEFERİNDE "
                    "çağrılmalıdır — çağrılmazsa tercih kaybolur.",
     "parameters": {"type": "object", "properties": {
         "text": {"type": "string"}}, "required": ["text"]}},
]

MAX_STEPS = 8


def _gemini_loop(context: ToolContext, message: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    gen_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=TOOL_DEFINITIONS)],
        temperature=0.3,
    )
    contents = [types.Content(role="user", parts=[types.Part(text=message)])]

    for _ in range(MAX_STEPS):
        response = client.models.generate_content(
            model=config.GEMINI_MODEL, contents=contents, config=gen_config)
        candidate = response.candidates[0].content
        calls = [p.function_call for p in (candidate.parts or []) if p.function_call]
        if not calls:
            return response.text or ""

        contents.append(candidate)
        result_parts = []
        for fc in calls:
            tool = getattr(context, fc.name, None)
            try:
                result = tool(**_clean_args(tool, dict(fc.args))) if tool else {"error": f"unknown tool {fc.name}"}
            except Exception as err:  # a tool error is reported to the agent, loop continues
                log.exception("Tool error: %s", fc.name)
                result = {"error": str(err)}
            result_parts.append(types.Part.from_function_response(
                name=fc.name, response={"result": result}))
        contents.append(types.Content(role="tool", parts=result_parts))

    return "Planı kurdum ama açıklamayı kısa kesmek zorunda kaldım — plan kartlarına bakabilirsin."


def _ensure_preference_persisted(context: ToolContext, message: str) -> None:
    """Code-level backstop for prompt rule 4 (same philosophy as the grounding
    guard): an LLM that says "not aldım" WITHOUT calling write_memory silently
    drops the preference. If the message states a preference and no write
    happened in this turn, persist it deterministically."""
    if not message or not fallback.is_preference(message):
        return
    if any(call.startswith("write_memory") for call in context.calls):
        return
    log.warning("LLM skipped write_memory for a preference; persisting via backstop")
    context.write_memory(message.strip())


def assistant_reply(user_id: int, profile: HouseholdProfile, message: str) -> AssistantResponse:
    context = ToolContext(user_id, profile)

    if config.GEMINI_API_KEY:
        try:
            text = _gemini_loop(context, message)
            _ensure_preference_persisted(context, message)
            # Honesty guard: never ship an LLM reply that invents figures.
            if context.last_plan is not None:
                bad = ungrounded_numbers(text, context.last_plan)
                if bad:
                    log.warning("Ungrounded numbers in agent reply: %s", bad)
                    text = fallback.reply(context, message)
                    return AssistantResponse(reply=text, plan=context.last_plan,
                                             agent_mode="fallback", tool_calls=context.calls)
            return AssistantResponse(reply=text, plan=context.last_plan,
                                     agent_mode="gemini", tool_calls=context.calls)
        except Exception:
            log.exception("Gemini orchestration failed, falling back")

    text = fallback.reply(context, message)
    return AssistantResponse(reply=text, plan=context.last_plan,
                             agent_mode="fallback", tool_calls=context.calls)
