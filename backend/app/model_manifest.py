"""Loads backend/app/models/manifest.json into ModelManifestEntry records.

Read-only diagnostics layer (docs/SPRINTS.md TDB-4): describes what's actually
deployed for each of the three model/algorithm components (production,
consumption, optimizer) — version, training date, metrics, data provenance.
Surfaced via /api/health. A missing or malformed manifest is reported as an
empty diagnostics result without affecting the customer-facing endpoints.
"""

import json
import logging
import os
from functools import lru_cache

from .schemas import ModelManifestEntry

log = logging.getLogger(__name__)

_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "models", "manifest.json")


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, ModelManifestEntry]:
    try:
        with open(_MANIFEST_PATH, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        log.exception("Model manifest unreadable at %s", _MANIFEST_PATH)
        return {}

    entries: dict[str, ModelManifestEntry] = {}
    for name, data in raw.items():
        try:
            entries[name] = ModelManifestEntry(**data)
        except Exception:
            log.exception("Manifest entry %r failed validation, dropping it", name)
    return entries
