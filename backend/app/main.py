"""Voltaic API — FastAPI uygulaması.

Uçlar mobil uygulamanın ekranlarıyla bire bir eşleşir:
  POST /api/kayit           → Onboarding
  GET  /api/plan/{id}       → Bugün ekranı (agent'sız hızlı plan)
  POST /api/asistan         → Asistan sohbeti (Gemini agent / fallback)
  GET  /api/rapor/{id}      → Ay sonu raporu (karşı-olgusal + CO2)
  GET  /api/bildirimler/{id}→ Proaktif uyarılar
  POST /api/geribildirim    → "Uyguladım / uygulamadım"
  GET  /api/cihaz-referans  → Onboarding cihaz kataloğu
"""

import json
import os
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config, db
from .agent import asistan_cevapla
from .agent.baglam import AracBaglami
from .schemas import (AsistanIstek, AsistanYanit, AylikRapor, GeriBildirim,
                      GunlukPlan, HaneProfili, KayitIstek, KayitYanit)
from .services.bildirim import bildirimler
from .services.rapor import aylik_rapor

app = FastAPI(title="Voltaic API", version="0.1.0",
              description="Çatı-GES enerji asistanı — Türkiye'ye özel")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


# Şema, uygulama içe aktarılırken hazırlanır (TestClient dahil her ortamda çalışır)
db.hazirla()


@app.get("/api/saglik")
def saglik():
    return {"durum": "ok", "agent": "gemini" if config.GEMINI_API_KEY else "fallback"}


@app.post("/api/kayit", response_model=KayitYanit)
def kayit(istek: KayitIstek):
    kullanici_id = db.kullanici_ekle(istek.profil)
    return KayitYanit(kullanici_id=kullanici_id,
                      mesaj=f"Hoş geldin! {istek.profil.panel_kw} kW'lık sistemin için hazırım.")


@app.put("/api/profil/{kullanici_id}")
def profil_guncelle(kullanici_id: int, profil: HaneProfili):
    if not db.kullanici_getir(kullanici_id):
        raise HTTPException(404, "Kullanıcı bulunamadı")
    db.kullanici_guncelle(kullanici_id, profil)
    return {"durum": "guncellendi"}


@app.get("/api/profil/{kullanici_id}", response_model=HaneProfili)
def profil_getir(kullanici_id: int):
    profil = db.kullanici_getir(kullanici_id)
    if not profil:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return profil


@app.get("/api/plan/{kullanici_id}", response_model=GunlukPlan)
def gunluk_plan(kullanici_id: int, gun: str = "bugun"):
    """Bugün ekranı: LLM'e gitmeden deterministik plan (hızlı ve ücretsiz).
    Asistan sohbeti ise agent üzerinden çalışır."""
    profil = db.kullanici_getir(kullanici_id)
    if not profil:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    baglam = AracBaglami(kullanici_id, profil)
    baglam.optimize(gun)
    return baglam.son_plan


@app.post("/api/asistan", response_model=AsistanYanit)
def asistan(istek: AsistanIstek):
    profil = db.kullanici_getir(istek.kullanici_id)
    if not profil:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return asistan_cevapla(istek.kullanici_id, profil, istek.mesaj)


@app.post("/api/geribildirim")
def geribildirim(gb: GeriBildirim):
    db.geribildirim_kaydet(gb.kullanici_id, gb.tarih, gb.kalem_ad, gb.uygulandi)
    return {"durum": "kaydedildi"}


@app.get("/api/rapor/{kullanici_id}", response_model=AylikRapor)
def rapor(kullanici_id: int, ay: str | None = None):
    if not db.kullanici_getir(kullanici_id):
        raise HTTPException(404, "Kullanıcı bulunamadı")
    ay = ay or date.today().strftime("%Y-%m")
    return aylik_rapor(kullanici_id, ay)


@app.get("/api/bildirimler/{kullanici_id}")
def bildirim_listesi(kullanici_id: int):
    profil = db.kullanici_getir(kullanici_id)
    if not profil:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    return {"bildirimler": bildirimler(profil)}


@app.get("/api/cihaz-referans")
def cihaz_referans():
    yol = os.path.join(os.path.dirname(__file__), "data", "cihazlar.json")
    with open(yol, encoding="utf-8") as f:
        return json.load(f)
