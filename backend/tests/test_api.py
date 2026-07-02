"""API duman testleri — kayıt → plan → asistan (fallback) → rapor akışı.

Gemini anahtarı gerektirmez; hava tool'u ağ yoksa sentetik profile düşer,
akış her ortamda çalışır.
"""

import os
import tempfile

os.environ["VOLTAIC_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.pop("GEMINI_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
config.GEMINI_API_KEY = ""
config.DB_PATH = os.environ["VOLTAIC_DB"]

from app.main import app  # noqa: E402

istemci = TestClient(app)

PROFIL = {
    "kullanici_tipi": "ev", "il": "İzmir", "enlem": 38.42, "boylam": 27.14,
    "panel_kw": 5.0, "batarya_kwh": 0, "batarya_guc_kw": 0,
    "fatura_kwh_aylik": 300, "tarife_tipi": "uc_zamanli",
    "cihazlar": [{"ad": "Çamaşır makinesi", "kwh": 1.0, "sure_saat": 2,
                  "en_erken": 8, "en_gec": 23}],
}


def _kayit() -> int:
    yanit = istemci.post("/api/kayit", json={"profil": PROFIL})
    assert yanit.status_code == 200
    return yanit.json()["kullanici_id"]


def test_saglik():
    yanit = istemci.get("/api/saglik")
    assert yanit.status_code == 200
    assert yanit.json()["agent"] == "fallback"


def test_uctan_uca_akis():
    kid = _kayit()

    # Günlük plan
    plan = istemci.get(f"/api/plan/{kid}?gun=yarin")
    assert plan.status_code == 200
    govde = plan.json()
    assert govde["kalemler"], "Plan en az bir kalem içermeli"
    assert govde["toplam_tasarruf_tl_max"] >= govde["toplam_tasarruf_tl_min"]

    # Asistan (fallback modunda gerekçeli Türkçe yanıt)
    yanit = istemci.post("/api/asistan", json={"kullanici_id": kid,
                                               "mesaj": "yarın için plan yapar mısın"})
    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["agent_modu"] == "fallback"
    assert "TL" in govde["yanit"]
    assert govde["arac_cagrilari"], "Şeffaflık: çağrılan tool listesi dolu olmalı"

    # İtiraz → hafızaya yazılır, plan değişir
    itiraz = istemci.post("/api/asistan", json={"kullanici_id": kid,
                                                "mesaj": "öğlen 12den önce evde yokum"})
    assert itiraz.status_code == 200
    assert any("hafiza_yaz" in c for c in itiraz.json()["arac_cagrilari"])

    # Geri bildirim + rapor
    tarih = plan.json()["tarih"]
    gb = istemci.post("/api/geribildirim", json={
        "kullanici_id": kid, "tarih": tarih,
        "kalem_ad": "Çamaşır makinesi", "uygulandi": True})
    assert gb.status_code == 200

    ay = tarih[:7]
    rapor = istemci.get(f"/api/rapor/{kid}?ay={ay}")
    assert rapor.status_code == 200
    assert rapor.json()["uygulanan_oneri"] >= 1

    # Proaktif bildirimler
    bildirim = istemci.get(f"/api/bildirimler/{kid}")
    assert bildirim.status_code == 200
    assert isinstance(bildirim.json()["bildirimler"], list)


def test_cihaz_referans():
    yanit = istemci.get("/api/cihaz-referans")
    assert yanit.status_code == 200
    assert len(yanit.json()["cihazlar"]) >= 5
