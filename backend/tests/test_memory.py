"""S2-5 semantic memory tests.

Hermetic like the rest of the suite: Gemini embeddings are replaced with a
deterministic bag-of-words fake, so no network/key is needed. Chroma-backed
tests are skipped when chromadb is not installed (it is an optional extra,
see requirements-semantic.txt) — the keyword-fallback tests always run.
"""

import hashlib
import os
import tempfile

os.environ["WATTRA_DB"] = os.path.join(tempfile.mkdtemp(), "memory_test.db")
os.environ.pop("GEMINI_API_KEY", None)

from app import config  # noqa: E402

config.DB_PATH = os.environ["WATTRA_DB"]
config.GEMINI_API_KEY = ""

import pytest  # noqa: E402

from app import db  # noqa: E402
from app.tools import memory  # noqa: E402

_NEXT_USER = iter(range(1000, 100000))


def _fake_embed(texts: list[str]) -> list[list[float]]:
    """Deterministic bag-of-words embedding: each word hashes into one of 64
    buckets. Texts sharing words get close vectors — enough to test ranking."""
    vectors = []
    for text in texts:
        vec = [0.0] * 64
        for word in text.casefold().split():
            bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % 64
            vec[bucket] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        vectors.append([v / norm for v in vec])
    return vectors


@pytest.fixture()
def user_id():
    db.init_db()
    return next(_NEXT_USER)


# --- Always-on behaviour (no chroma, no key) ---------------------------------

def test_write_and_read_signatures_unchanged(user_id):
    result = memory.write_memory(user_id, "salı öğlen evde yokum")
    assert result == {"status": "saved", "text": "salı öğlen evde yokum"}
    prefs = memory.read_memory(user_id)
    assert prefs and prefs[0]["text"] == "salı öğlen evde yokum"
    assert set(prefs[0]) == {"text", "source", "date"}


def test_keyword_fallback_ranks_word_overlap(user_id):
    memory.write_memory(user_id, "çamaşır makinesi gece çalışmasın gürültü oluyor")
    memory.write_memory(user_id, "salı öğlen evde yokum")
    hits = memory.search_preferences(user_id, "gece gürültü istemiyorum")
    assert hits[0]["text"].startswith("çamaşır makinesi gece")
    assert hits[0]["similarity"] > 0


def test_keyword_fallback_returns_recent_when_no_match(user_id):
    memory.write_memory(user_id, "salı öğlen evde yokum")
    hits = memory.search_preferences(user_id, "xyzq")
    assert hits and "similarity" not in hits[0]


# --- Semantic layer (needs chromadb; embeddings are faked) --------------------

@pytest.fixture()
def semantic(monkeypatch, tmp_path):
    pytest.importorskip("chromadb")
    monkeypatch.setattr(config, "SEMANTIC_MEMORY_ENABLED", True)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(config, "CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setattr(memory, "_embed_texts", _fake_embed)


def test_semantic_search_finds_similar_meaning(user_id, semantic):
    memory.write_memory(user_id, "salı öğlen evde yokum")
    memory.write_memory(user_id, "bulaşık makinesi sabah çalışsın")
    hits = memory.search_preferences(user_id, "salı günü evde olmayacağım")
    assert hits[0]["text"] == "salı öğlen evde yokum"
    assert hits[0]["similarity"] > hits[-1]["similarity"] or len(hits) == 1


def test_semantic_results_are_per_user(user_id, semantic):
    other = next(_NEXT_USER)
    memory.write_memory(user_id, "salı öğlen evde yokum")
    memory.write_memory(other, "klima aksam calissin")
    hits = memory.search_preferences(user_id, "salı evde yokum")
    assert all(h["text"] != "klima aksam calissin" for h in hits)


def test_backfill_indexes_pre_semantic_rows(user_id, semantic, monkeypatch):
    # Row written while the semantic layer was OFF...
    monkeypatch.setattr(config, "SEMANTIC_MEMORY_ENABLED", False)
    memory.write_memory(user_id, "termosifon gece devrede olsun")
    # ...is still found once the layer comes back (backfill on search).
    monkeypatch.setattr(config, "SEMANTIC_MEMORY_ENABLED", True)
    hits = memory.search_preferences(user_id, "termosifon gece")
    assert hits and hits[0]["text"] == "termosifon gece devrede olsun"


def test_embedding_failure_never_loses_the_preference(user_id, semantic, monkeypatch):
    def _boom(texts):
        raise RuntimeError("embedding API down")
    monkeypatch.setattr(memory, "_embed_texts", _boom)
    result = memory.write_memory(user_id, "fırın hafta sonu kullanılmıyor")
    assert result["status"] == "saved"
    prefs = memory.read_memory(user_id)
    assert prefs[0]["text"] == "fırın hafta sonu kullanılmıyor"
    # Search also survives: falls back to keyword matching.
    hits = memory.search_preferences(user_id, "fırın hafta sonu")
    assert hits and hits[0]["text"] == "fırın hafta sonu kullanılmıyor"
