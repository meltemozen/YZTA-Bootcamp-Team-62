"""Wattra configuration — ALL energy constants and their sources live HERE.

No price/factor constant exists anywhere else in the code. Each value carries
its source and date; after an EPDK board decision (usually Jan/Apr/Jul) this
file is updated and the date is recorded in docs/METHOD.md.

── REGULATORY SUMMARY (as of July 2026) ────────────────────────────────────────
* Residential single-rate tariff is TIERED: low tier up to 240 kWh/month,
  high tier above (EPDK, 4 April 2026 tariff table).
* Three-zone tariff has NO tiers. Bands are fixed nationwide:
  day 06-17, peak 17-22, night 22-06.
* NET-METERING IS HOURLY: the 2 April 2026 Official Gazette removed monthly
  netting; from 1 May 2026 production/consumption net out per HOUR. Surplus
  within an hour is exported and bought back at a price with distribution fees
  and taxes REMOVED (about 70% of the retail price). This makes self-consumption
  profitable every hour — the economic basis of the optimizer.
* Residential rooftop PV net-metering upper limit is 10 kW.
"""

import os

# --- LLM ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "0").lower() in ("1", "true", "yes", "on")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OLLAMA_TIMEOUT_S = float(os.getenv("OLLAMA_TIMEOUT_S", "45"))

# --- Database ---
DB_PATH = os.getenv("WATTRA_DB", os.path.join(os.path.dirname(__file__), "..", "wattra.db"))

# --- Semantic memory (S2-5) ---
# Optional Chroma + Gemini-embedding layer over the SQLite preference store.
# Degrades to keyword search when the flag is off, chromadb is not installed
# or there is no GEMINI_API_KEY — the product never depends on it.
SEMANTIC_MEMORY_ENABLED = os.getenv("WATTRA_SEMANTIC_MEMORY", "1").lower() in ("1", "true", "yes", "on")
CHROMA_PATH = os.getenv("WATTRA_CHROMA_PATH", os.path.join(os.path.dirname(__file__), "..", "chroma"))
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")

# --- EPDK tariff (end-user price incl. taxes, TL/kWh) ---
# Source: EPDK 4 April 2026 tariff table; sector compilations (June 2026).
# Three-zone VAT-excl. base: day 4.38, peak 6.17, night 2.94
# → with taxes (VAT 20% + consumption tax + energy fund) ≈ ×1.27.
TARIFF = {
    "residential": {
        # Tiered single-rate: monthly threshold and two prices
        "tier_threshold_kwh_month": 240,
        "single_low": 3.24,
        "single_high": 4.86,
        "three_zone": {"day": 5.57, "peak": 7.85, "night": 3.74},
    },
    "commercial": {
        # Commercial tier threshold: daily 30 kWh ≈ monthly 900 kWh
        "tier_threshold_kwh_month": 900,
        "single_low": 4.45,
        "single_high": 5.15,
        # Commercial three-zone — APPROXIMATE (varies with regional distribution
        # fee); to be confirmed against the supplier's table before delivery.
        "three_zone": {"day": 5.80, "peak": 8.20, "night": 3.90},
    },
}

# Optional research/adapter hook: point this to a JSON file with 24-hour
# `hourly_price` and optionally `hourly_sell_price` arrays to test dynamic
# price-vector dispatch without changing the optimizer.
PRICE_VECTOR_FILE = os.getenv("WATTRA_PRICE_VECTOR_FILE", "")

# In hourly net-metering the sell price of surplus energy = that hour's retail
# price − distribution fee − taxes ≈ retail × this ratio.
# (Sector example: residential ~3.5 TL/kWh sell ↔ ~4.86 buy → ≈0.72)
NETMETER_SELL_RATIO = 0.70

# Residential rooftop PV net-metering limit (Unlicensed Generation Regulation)
RESIDENTIAL_NETMETER_LIMIT_KW = 10.0

TIME_BANDS = {"day": range(6, 17), "peak": range(17, 22), "night": list(range(22, 24)) + list(range(0, 6))}

# --- PV production model (v0 physical model) ---
PV_PERFORMANCE_RATIO = 0.80     # wiring, inverter, soiling losses
PV_TEMP_COEFF = 0.004           # power loss / °C (cell temp above 25°C)
PV_NOCT_FACTOR = 0.03           # cell temp ≈ air + 0.03 × irradiance

# --- Carbon and environmental equivalents ---
# TR grid emission factor — Ministry of Energy "National Electricity Grid
# Emission Factor Info Form" (rev. 03.2024): generation EF ≈ 0.434-0.439 tCO2e/MWh.
CO2_KG_PER_KWH = 0.44
# Annual CO2 absorption of a mature tree (EPA / One Tree Planted avg value)
TREE_KG_CO2_YEAR = 22.0
# Average passenger car emission (TR fleet average approximation, kg CO2/km)
CAR_KG_CO2_KM = 0.17

# --- Uncertainty ---
# Because the consumption profile relies on bill calibration, TL savings are
# shown to the user as a range rather than a single figure.
SAVING_UNCERTAINTY = 0.25  # ±25%
