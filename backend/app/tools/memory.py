"""read_memory / write_memory tools.

The agent's "learning memory": user preferences ("nobody is home Tuesday
afternoons") and agent inferences are kept here; read on every plan generation
and fed into the Gemini context.

The MVP backend is SQLite. Extension point for YZ-3: if semantic search is
wanted, add Chroma and a `search_preferences(query)` function to this module —
the tool signatures do not change.
"""

from .. import db


def read_memory(user_id: int) -> list[dict]:
    return db.preferences(user_id)


def write_memory(user_id: int, text: str, source: str = "user") -> dict:
    db.add_preference(user_id, text, source)
    return {"status": "saved", "text": text}
