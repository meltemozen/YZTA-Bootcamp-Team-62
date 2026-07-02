"""SQLite kalıcılık katmanı — kullanıcı, tercih (hafıza), öneri geçmişi,
geri bildirim. Stdlib sqlite3; ek bağımlılık yok, Docker'da dosya volume'u
ile kalıcı.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

from . import config
from .schemas import GunlukPlan, HaneProfili

_SEMA = """
CREATE TABLE IF NOT EXISTS kullanici (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profil TEXT NOT NULL,
    olusturma TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tercih (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_id INTEGER NOT NULL,
    metin TEXT NOT NULL,
    kaynak TEXT NOT NULL DEFAULT 'kullanici',
    tarih TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS oneri (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_id INTEGER NOT NULL,
    tarih TEXT NOT NULL,
    plan TEXT NOT NULL,
    UNIQUE(kullanici_id, tarih)
);
CREATE TABLE IF NOT EXISTS geribildirim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_id INTEGER NOT NULL,
    tarih TEXT NOT NULL,
    kalem_ad TEXT NOT NULL,
    uygulandi INTEGER NOT NULL,
    UNIQUE(kullanici_id, tarih, kalem_ad)
);
"""


@contextmanager
def baglanti():
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def hazirla() -> None:
    with baglanti() as con:
        con.executescript(_SEMA)


# --- Kullanıcı ---

def kullanici_ekle(profil: HaneProfili) -> int:
    with baglanti() as con:
        imlec = con.execute(
            "INSERT INTO kullanici (profil, olusturma) VALUES (?, ?)",
            (profil.model_dump_json(), datetime.now().isoformat()))
        return imlec.lastrowid


def kullanici_getir(kullanici_id: int) -> HaneProfili | None:
    with baglanti() as con:
        satir = con.execute("SELECT profil FROM kullanici WHERE id = ?",
                            (kullanici_id,)).fetchone()
    return HaneProfili.model_validate_json(satir["profil"]) if satir else None


def kullanici_guncelle(kullanici_id: int, profil: HaneProfili) -> None:
    with baglanti() as con:
        con.execute("UPDATE kullanici SET profil = ? WHERE id = ?",
                    (profil.model_dump_json(), kullanici_id))


# --- Hafıza (tercihler) ---

def tercih_ekle(kullanici_id: int, metin: str, kaynak: str = "kullanici") -> None:
    with baglanti() as con:
        con.execute(
            "INSERT INTO tercih (kullanici_id, metin, kaynak, tarih) VALUES (?, ?, ?, ?)",
            (kullanici_id, metin, kaynak, datetime.now().isoformat()))


def tercihler(kullanici_id: int, limit: int = 20) -> list[dict]:
    with baglanti() as con:
        satirlar = con.execute(
            "SELECT metin, kaynak, tarih FROM tercih WHERE kullanici_id = ? "
            "ORDER BY id DESC LIMIT ?", (kullanici_id, limit)).fetchall()
    return [dict(s) for s in satirlar]


# --- Öneri geçmişi + geri bildirim (karşı-olgusal raporun ham verisi) ---

def oneri_kaydet(kullanici_id: int, plan: GunlukPlan) -> None:
    with baglanti() as con:
        con.execute(
            "INSERT INTO oneri (kullanici_id, tarih, plan) VALUES (?, ?, ?) "
            "ON CONFLICT(kullanici_id, tarih) DO UPDATE SET plan = excluded.plan",
            (kullanici_id, plan.tarih.isoformat(), plan.model_dump_json()))


def oneriler_ay(kullanici_id: int, ay: str) -> list[GunlukPlan]:
    """ay: 'YYYY-MM'"""
    with baglanti() as con:
        satirlar = con.execute(
            "SELECT plan FROM oneri WHERE kullanici_id = ? AND tarih LIKE ?",
            (kullanici_id, f"{ay}-%")).fetchall()
    return [GunlukPlan.model_validate_json(s["plan"]) for s in satirlar]


def geribildirim_kaydet(kullanici_id: int, tarih: date, kalem_ad: str,
                        uygulandi: bool) -> None:
    with baglanti() as con:
        con.execute(
            "INSERT INTO geribildirim (kullanici_id, tarih, kalem_ad, uygulandi) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(kullanici_id, tarih, kalem_ad) DO UPDATE SET uygulandi = excluded.uygulandi",
            (kullanici_id, tarih.isoformat(), kalem_ad, int(uygulandi)))


def geribildirimler_ay(kullanici_id: int, ay: str) -> list[dict]:
    with baglanti() as con:
        satirlar = con.execute(
            "SELECT tarih, kalem_ad, uygulandi FROM geribildirim "
            "WHERE kullanici_id = ? AND tarih LIKE ?",
            (kullanici_id, f"{ay}-%")).fetchall()
    return [dict(s) for s in satirlar]
