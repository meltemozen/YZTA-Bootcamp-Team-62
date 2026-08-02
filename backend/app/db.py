"""SQLite persistence layer — users, preferences (memory), plan history,
feedback. Stdlib sqlite3; no extra dependency, persistent in Docker via a
file volume.
"""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

from . import config
from .schemas import DailyPlan, HouseholdProfile

_SCHEMA = """
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password_hash TEXT,
    name TEXT DEFAULT '',
    is_admin INTEGER NOT NULL DEFAULT 0,
    profile TEXT NOT NULL,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS preference (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'user',
    date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    plan TEXT NOT NULL,
    UNIQUE(user_id, date)
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    item_name TEXT NOT NULL,
    applied INTEGER NOT NULL,
    UNIQUE(user_id, date, item_name)
);
"""

@contextmanager
def connect():
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _columns(con, table: str) -> set[str]:
    return {row["name"] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}


def _migrate_user_auth_columns(con) -> None:
    """Upgrade pre-auth SQLite files in place.

    SQLite cannot add a UNIQUE column via ALTER TABLE. Add email as nullable
    text, then enforce uniqueness with a partial unique index.
    """
    cols = _columns(con, "user")
    if "email" not in cols:
        con.execute("ALTER TABLE user ADD COLUMN email TEXT")
    if "password_hash" not in cols:
        con.execute("ALTER TABLE user ADD COLUMN password_hash TEXT")
    if "name" not in cols:
        con.execute("ALTER TABLE user ADD COLUMN name TEXT DEFAULT ''")
    if "is_admin" not in cols:
        con.execute("ALTER TABLE user ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    con.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_email_unique "
        "ON user(email) WHERE email IS NOT NULL"
    )


def init_db() -> None:
    with connect() as con:
        con.executescript(_SCHEMA)
        # Run migrations for pre-auth databases (columns already exist → skip).
        _migrate_user_auth_columns(con)


# --- User (legacy — backward-compatible with the old register flow) ---

def add_user(profile: HouseholdProfile) -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO user (profile, created) VALUES (?, ?)",
            (profile.model_dump_json(), datetime.now().isoformat()))
        return cur.lastrowid


def get_user(user_id: int) -> HouseholdProfile | None:
    with connect() as con:
        row = con.execute("SELECT profile FROM user WHERE id = ?",
                          (user_id,)).fetchone()
    if not row or row["profile"] in (None, "null", ""):
        return None
    return HouseholdProfile.model_validate_json(row["profile"])


def update_user(user_id: int, profile: HouseholdProfile) -> None:
    with connect() as con:
        con.execute("UPDATE user SET profile = ? WHERE id = ?",
                    (profile.model_dump_json(), user_id))


# --- User (auth) ---

def create_auth_user(email: str, password_hash: str, name: str,
                     profile: HouseholdProfile | None = None) -> int:
    """Register a new user with e-mail + hashed password."""
    with connect() as con:
        cur = con.execute(
            "INSERT INTO user (email, password_hash, name, profile, created) "
            "VALUES (?, ?, ?, ?, ?)",
            (email.lower().strip(), password_hash, name.strip(),
             profile.model_dump_json() if profile else "null", datetime.now().isoformat()))
        return cur.lastrowid


def get_user_by_email(email: str) -> dict | None:
    """Return ``{id, email, password_hash, name, profile}`` or *None*."""
    with connect() as con:
        row = con.execute(
            "SELECT id, email, password_hash, name, is_admin, profile FROM user "
            "WHERE email = ?", (email.lower().strip(),)).fetchone()
    return dict(row) if row else None


def get_user_auth_info(user_id: int) -> dict | None:
    """Return ``{id, email, name, profile}`` for the profile screen."""
    with connect() as con:
        row = con.execute(
            "SELECT id, email, name, is_admin, profile FROM user WHERE id = ?",
            (user_id,)).fetchone()
    return dict(row) if row else None


def update_user_name(user_id: int, name: str) -> None:
    with connect() as con:
        con.execute("UPDATE user SET name = ? WHERE id = ?",
                    (name.strip(), user_id))


def update_user_email(user_id: int, email: str) -> None:
    with connect() as con:
        con.execute("UPDATE user SET email = ? WHERE id = ?",
                    (email.lower().strip(), user_id))


def update_user_password(user_id: int, password_hash: str) -> None:
    with connect() as con:
        con.execute("UPDATE user SET password_hash = ? WHERE id = ?",
                    (password_hash, user_id))


def set_user_admin(user_id: int, is_admin: bool = True) -> None:
    with connect() as con:
        con.execute("UPDATE user SET is_admin = ? WHERE id = ?",
                    (1 if is_admin else 0, user_id))


def is_user_admin(user_id: int) -> bool:
    with connect() as con:
        row = con.execute("SELECT is_admin FROM user WHERE id = ?", (user_id,)).fetchone()
    return bool(row and row["is_admin"])


# --- Memory (preferences) ---

def add_preference(user_id: int, text: str, source: str = "user") -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO preference (user_id, text, source, date) VALUES (?, ?, ?, ?)",
            (user_id, text, source, datetime.now().isoformat()))
        return cur.lastrowid


def preferences(user_id: int, limit: int = 20) -> list[dict]:
    with connect() as con:
        rows = con.execute(
            "SELECT text, source, date FROM preference WHERE user_id = ? "
            "ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
    return [dict(r) for r in rows]


def preferences_with_ids(user_id: int) -> list[dict]:
    """All preferences incl. row ids — used by the semantic index backfill."""
    with connect() as con:
        rows = con.execute(
            "SELECT id, text, source, date FROM preference WHERE user_id = ? "
            "ORDER BY id", (user_id,)).fetchall()
    return [dict(r) for r in rows]


# --- Plan history + feedback (raw data for the counterfactual report) ---

def save_plan(user_id: int, plan: DailyPlan) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO plan (user_id, date, plan) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, date) DO UPDATE SET plan = excluded.plan",
            (user_id, plan.date.isoformat(), plan.model_dump_json()))


def plans_for_month(user_id: int, month: str) -> list[DailyPlan]:
    """month: 'YYYY-MM'"""
    with connect() as con:
        rows = con.execute(
            "SELECT plan FROM plan WHERE user_id = ? AND date LIKE ?",
            (user_id, f"{month}-%")).fetchall()
    return [DailyPlan.model_validate_json(r["plan"]) for r in rows]


def save_feedback(user_id: int, date_: date, item_name: str,
                  applied: bool) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO feedback (user_id, date, item_name, applied) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, date, item_name) DO UPDATE SET applied = excluded.applied",
            (user_id, date_.isoformat(), item_name, int(applied)))


def feedback_for_month(user_id: int, month: str) -> list[dict]:
    with connect() as con:
        rows = con.execute(
            "SELECT date, item_name, applied FROM feedback "
            "WHERE user_id = ? AND date LIKE ?",
            (user_id, f"{month}-%")).fetchall()
    return [dict(r) for r in rows]
