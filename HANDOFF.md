# HANDOFF — Wattra (AI agent onboarding)

> Read this first. It gets an AI agent (or a new developer) productive in minutes:
> what the system is, the rules you must not break, how to verify, where we left
> off, and what to work on next. Detailed docs are linked inline.

## 1. What Wattra is?

Agent-based rooftop-solar energy assistant for Turkey. It forecasts a household's
solar **production** and electricity **consumption**, then — given Turkey's tiered /
three-zone tariff and **hourly net-metering** rules — tells the user in plain Turkish
"run this device / (dis)charge the battery at this hour", proves the saving in TL +
CO₂, learns preferences, and warns proactively. Two ML models run as **tools** the
agent calls; a Gemini function-calling loop is the agent.

Bootcamp: Google YZTA 2026, AI & Data Science category. Delivery 2 Aug 2026.

## 2. Non-negotiable rules (break these and you break the project)

1. **Code = English, mobile UI = Turkish.** All identifiers (files, functions,
   classes, vars, tool names, API routes, JSON fields, enum values) are English.
   Every string a user sees in the mobile app stays Turkish (screens, alerts,
   agent replies, device names). Turkish is also fine in doc prose/comments.
2. **The model–agent contract is LOCKED.** `backend/app/schemas.py` (+ `docs/CONTRACT.md`)
   define tool signatures and JSON shapes. Do NOT change field names/shapes without
   updating BOTH backend and mobile and the contract doc. Swapping a model means
   changing a function BODY only (see §6), never the signature/schema.
3. **Never commit secrets.** `GEMINI_API_KEY` is read via `os.getenv` only; `.env`
   is gitignored. No keys in code, tests, or fixtures.
4. **Keep it working.** Backend has 27 tests + ruff lint; both must stay green
   (CI enforces on every push/PR). Mobile UI must remain runnable.

## 3. Architecture

```
Open-Meteo (live) ┐                         ┌ get_weather
PVGIS (history)   ┤  ML tool layer (VB)     ├ forecast_production   (v0 physical → v1 weather artifact)
EPDK tariff       ┤  + rule engines         ├ forecast_consumption  (bill calibration → v1)
Bill (calibration)┘                         ├ get_tariff            (tiers + hourly net-metering)
                                            ├ optimize              (deterministic plan)
                                            └ read_memory/write_memory (SQLite → Chroma)
                         │ tools
                         ▼
        Gemini function-calling agent (YZ)  ── no key? rule-based fallback (never stalls)
                         │ REST (FastAPI)
                         ▼
        Expo single codebase → Android/iOS app + website (Turkish UI)
```

Economic core: in **hourly net-metering** (Official Gazette 02.04.2026, effective
1 May 2026) the sell price is ~30% below buy every hour, so self-consumption always
beats exporting — this is why the optimizer shifts loads into solar hours.

## 4. Repo map

| Path | What |
|---|---|
| `backend/app/schemas.py` | **Locked contract** (Pydantic) |
| `backend/app/config.py` | **All** energy constants + regulatory sources (single source of truth) |
| `backend/app/tools/` | 6 tools: `weather`, `production`, `consumption`, `tariff`, `optimize`, `memory` |
| `backend/app/agent/` | `orchestrator` (Gemini loop) · `context` (tool surface) · `fallback` (rule-based) |
| `backend/app/services/` | `report` (monthly/counterfactual) · `notifications` (proactive) |
| `backend/tests/` | `test_core.py` (logic) · `test_api.py` (API smoke) |
| `mobile/src/{screens,components}` | 5 screens + chart/cards/brand; `api.js`, `theme.js` |
| `data/scripts/pvgis_fetch.py` | PVGIS training-data fetcher (VB) |
| `docs/` | `CONTRACT` · `METHOD` (data/legis. sources) · `TEKNIK` · `DEPLOY` · `SPRINTS` · `scrum/` |

## 5. Run & verify

```bash
# Backend
cd backend && pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000      # http://localhost:8000/docs
python -m pytest tests/ -q                      # 27 tests, no network needed
ruff check .                                     # lint (CI runs this)

# Mobile (needs node_modules; Turkish UI)
cd mobile && npm install && npx expo start       # phone via Expo Go, or --web
# No node_modules? Syntax-check a file: npx esbuild src/screens/Today.js --loader:.js=jsx >/dev/null
```

Health check: `GET /api/health` → `{"agent":"gemini"}` if a key is set, else `"fallback"`.
Env: `GEMINI_API_KEY` (optional), `GEMINI_MODEL`, `WATTRA_DB`, `WATTRA_CORS_ORIGINS`, `LOG_LEVEL`.

## 6. Where we left off & what to work on next

**Done (Sprint 1):** end-to-end working product with **baseline** models, real agent
(tool-use + memory + negotiation), mobile+web, grounding guard, agent evals, tests,
CI, English codebase. See [docs/scrum/sprint-1](docs/scrum/sprint-1/).

**Next (Sprint 2–3):** full backlog with paste-ready descriptions in
[docs/SPRINTS.md](docs/SPRINTS.md). The highest-value, clearly-scoped extension points:

| Area | File (change the BODY only) | Task |
|---|---|---|
| Production model → weather-aware artifact | `backend/app/tools/production.py` | S2-1 — keep signature + `ProductionForecast`, set `model_version="v1-weather-regressor"`, retrain from PVGIS/Open-Meteo CSVs |
| Consumption model → smart-meter shape artifact | `backend/app/tools/consumption.py` | S2-2 — same rule; validate shape vs EPİAŞ/public smart-meter profile (S2-3) |
| Semantic memory → Chroma | `backend/app/tools/memory.py` | S2-5 — add `search_preferences(query)`, keep read/write signatures; fall back to SQLite without a store |
| Agent prompt hardening | `backend/app/agent/orchestrator.py` | S2-4 — tune `SYSTEM_PROMPT`/tool descriptions against a live key |
| Deploy | `mobile/app.json`, Docker | S3-2 — Railway/Cloud Run + EAS APK |

**Model swap checklist:** change only the function body → `python -m pytest tests/`
still green → `model_version` bumped → agent/API/mobile untouched. That's the whole
point of the locked contract.

## 7. Gotchas

- `google-genai` is imported **lazily** inside `orchestrator._gemini_loop`; the app
  imports and tests run without it. With no key, everything uses the deterministic
  fallback and is honestly marked `agent_mode="fallback"`.
- Tests are hermetic: `weather.py` falls back to cache→synthetic offline, so no
  network is needed. Don't add tests that hit live APIs into the gating suite.
- All hourly arrays are exactly 24 elements (local 00:00–23:00).
- Saving figures are **ranges** (consumption is bill-calibrated, ±25%); never present
  a single hard TL number. Reports say "simulation", not meter readings.
- The mobile transparency footer shows raw tool-call names (English) — that's a
  technical/debug element, acceptable in the Turkish UI.

## 8. Future research (NOT in current sprints — keep in mind)

**Real solar-panel / smart-meter hardware integration.** Today the user types panel
kW and bill kWh; a production v2 could read real telemetry. Concrete leads to research:

- **Inverter cloud APIs:** SolarEdge Monitoring API, Huawei FusionSolar, Fronius Solar
  API (local REST on the inverter), SMA, Enphase Enlighten — pull real production per
  15-min/hour and replace/augment `forecast_production` with actuals + short-horizon forecast.
- **Local/standard protocols:** SunSpec **Modbus TCP** (vendor-neutral inverter register
  model), **MQTT** telemetry, Home Assistant energy integrations for on-prem read.
- **Smart meters (Turkey):** OSOS (Otomatik Sayaç Okuma Sistemi) / distribution-company
  data and EPİAŞ transparency for real consumption; would replace bill calibration with
  measured hourly load.
- **Battery/EMS:** inverter/EMS control APIs to not just *advise* but *actuate*
  charge/discharge (moves the product from advisor to controller — regulatory + safety
  work needed).

Design note: any of these plugs in behind the **existing tool contract** — e.g. a
`production.py` that prefers live inverter data and falls back to the model — so the
agent, API and UI don't change. That is exactly what the locked contract buys us.
