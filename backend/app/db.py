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


def init_db() -> None:
    with connect() as con:
        con.executescript(_SCHEMA)


# --- User ---

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
    return HouseholdProfile.model_validate_json(row["profile"]) if row else None


def update_user(user_id: int, profile: HouseholdProfile) -> None:
    with connect() as con:
        con.execute("UPDATE user SET profile = ? WHERE id = ?",
                    (profile.model_dump_json(), user_id))


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
