"""read_memory / write_memory / search_preferences tools.

The agent's "learning memory": user preferences ("nobody is home Tuesday
afternoons") and agent inferences are kept here; read on every plan generation
and fed into the Gemini context.

SQLite is the source of truth (S1). S2-5 adds an optional semantic layer:
every preference is ALSO embedded (Gemini embedding API) into a local Chroma
collection, so `search_preferences(query)` retrieves similar past preferences
by MEANING, not just keywords. The layer is strictly best-effort — without the
feature flag, the chromadb package or a GEMINI_API_KEY it degrades to a
dependency-free keyword match over SQLite; the product never stalls (same
philosophy as the agent fallback). The locked read/write signatures are
unchanged; search_preferences is an additive tool (CONTRACT.md v1.3).
"""

import logging
from datetime import datetime

from .. import config, db

log = logging.getLogger(__name__)

_COLLECTION_NAME = "preferences"


# --- Semantic layer (optional) ------------------------------------------------

def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Gemini embedding call — isolated in one place so tests can monkeypatch
    it with a deterministic fake (the gating suite must stay offline)."""
    from google import genai

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    result = client.models.embed_content(model=config.GEMINI_EMBED_MODEL, contents=texts)
    return [list(e.values) for e in result.embeddings]


def _collection():
    """The Chroma collection, or None when the semantic layer is unavailable.
    Embeddings are always supplied explicitly, so Chroma's default embedding
    model (an English-centric ONNX download) is never triggered."""
    if not (config.SEMANTIC_MEMORY_ENABLED and config.GEMINI_API_KEY):
        return None
    try:
        import chromadb
    except ImportError:
        return None
    try:
        client = chromadb.PersistentClient(path=config.CHROMA_PATH)
        return client.get_or_create_collection(
            _COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    except Exception:
        log.exception("Chroma unavailable; semantic memory disabled for this call")
        return None


def _backfill(col, user_id: int) -> None:
    """Index this user's SQLite preferences that are not yet in Chroma.
    Idempotent: existing ids are skipped, so pre-semantic-era rows (or rows
    written while the embedding API was down) get indexed on the next search."""
    rows = db.preferences_with_ids(user_id)
    if not rows:
        return
    ids = [f"{user_id}:{r['id']}" for r in rows]
    existing = set(col.get(ids=ids).get("ids", []))
    missing = [(i, r) for i, r in zip(ids, rows) if i not in existing]
    if not missing:
        return
    vectors = _embed_texts([r["text"] for _, r in missing])
    col.add(
        ids=[i for i, _ in missing],
        embeddings=vectors,
        documents=[r["text"] for _, r in missing],
        metadatas=[{"user_id": user_id, "source": r["source"], "date": r["date"]}
                   for _, r in missing],
    )


def _keyword_search(user_id: int, query: str, top_k: int) -> list[dict]:
    """Dependency-free fallback: casefolded word overlap over recent
    preferences. No hit at all → most recent ones are still useful context."""
    words = {w for w in query.casefold().split() if len(w) > 2}
    prefs = db.preferences(user_id, limit=50)
    scored = []
    for pref in prefs:
        overlap = words & {w for w in pref["text"].casefold().split() if len(w) > 2}
        if overlap:
            scored.append((len(overlap), pref))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if scored:
        return [dict(pref, similarity=round(min(1.0, count / max(len(words), 1)), 3))
                for count, pref in scored[:top_k]]
    return prefs[:top_k]


# --- Tool surface ---------------------------------------------------------------

def read_memory(user_id: int) -> list[dict]:
    return db.preferences(user_id)


def write_memory(user_id: int, text: str, source: str = "user") -> dict:
    pref_id = db.add_preference(user_id, text, source)
    col = _collection()
    if col is not None:
        try:
            col.add(
                ids=[f"{user_id}:{pref_id}"],
                embeddings=_embed_texts([text]),
                documents=[text],
                metadatas=[{"user_id": user_id, "source": source,
                            "date": datetime.now().isoformat()}],
            )
        except Exception:
            # SQLite copy is safe; the backfill indexes this row on next search.
            log.exception("Semantic index write failed")
    return {"status": "saved", "text": text}


def search_preferences(user_id: int, query: str, top_k: int = 5) -> list[dict]:
    """Similar past preferences for a free-text query. Chroma + Gemini
    embeddings when available; otherwise keyword match. Result rows keep the
    read_memory shape (text/source/date) plus a `similarity` score."""
    col = _collection()
    if col is not None:
        try:
            _backfill(col, user_id)
            owned = col.get(where={"user_id": user_id}).get("ids", [])
            if owned:
                res = col.query(
                    query_embeddings=_embed_texts([query]),
                    n_results=min(top_k, len(owned)),
                    where={"user_id": user_id},
                )
                return [
                    {"text": doc, "source": meta.get("source", "user"),
                     "date": meta.get("date", ""),
                     "similarity": round(1 - dist, 3)}
                    for doc, meta, dist in zip(res["documents"][0],
                                               res["metadatas"][0],
                                               res["distances"][0])
                ]
        except Exception:
            log.exception("Semantic search failed; using keyword fallback")
    return _keyword_search(user_id, query, top_k)
