# Teknik Dokümantasyon

> Kod dili İngilizce (dosya/metot/alan adları); açıklama ve mobil arayüz
> Türkçe. Kontrat: [CONTRACT.md](CONTRACT.md).

## Mimari

```
Open-Meteo ─┐                          ┌─ get_weather
PVGIS ──────┤   ML Model Katmanı (VB)  ├─ forecast_production  (v0 physical → v1 LightGBM)
EPDK tarife ┤   + kural motorları      ├─ forecast_consumption (fatura kalibrasyonu)
Fatura ─────┘                          ├─ get_tariff           (kademe + saatlik mahsup)
                                       ├─ optimize             (deterministik plan)
                                       └─ read_memory/write_memory  (SQLite)
                        │ tool'lar
                        ▼
        Gemini Agent (function-calling döngüsü, YZ)
        · kendi kararıyla tool çağırır · itiraza yeniden planlar
        · anahtar yoksa kural tabanlı fallback (ürün asla durmaz)
                        │ REST (FastAPI)
                        ▼
        Expo tek kod tabanı → Android/iOS uygulaması + web sitesi
```

## Depo yapısı

| Yol | İçerik | Sahibi |
|---|---|---|
| `backend/app/schemas.py` | **Model–agent kontratı (KİLİTLİ, v1.2)** | Ortak |
| `backend/app/config.py` | Tüm enerji sabitleri + mevzuat kaynakları | Ortak |
| `backend/app/tools/` | 6 tool: weather, production, consumption, tariff, optimize, memory | VB+YZ |
| `backend/app/agent/` | Gemini orchestrator + context + fallback | YZ |
| `backend/app/services/` | Ay sonu raporu (report), proaktif bildirim (notifications) | YZ |
| `backend/tests/` | 14 çekirdek + API testi (`test_core.py`, `test_api.py`) | Ortak |
| `mobile/` | Expo uygulaması (5 ekran + grafik) — mobil ve web | YZ-3 |
| `data/scripts/pvgis_fetch.py` | PVGIS eğitim verisi çekme | VB |
| `docs/` | CONTRACT · METHOD · DEPLOY · TEKNIK | Ortak |

## Hızlı başlangıç

```bash
# Backend (dev: requirements-dev.txt = runtime + pytest + ruff)
cd backend && python -m venv .venv && .venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
# → http://localhost:8000/docs

# Mobil + Web (ayrı terminal)
cd mobile && npm install
npx expo start          # telefon: Expo Go ile QR okut
npx expo start --web    # tarayıcı: http://localhost:8081
```

Testler: `cd backend && python -m pytest tests/ -v` (14/14, ağ gerektirmez).
Ayrıntılı çalıştırma/deploy: [DEPLOY.md](DEPLOY.md)

## Tasarım kimliği

"Gece şebekesi" koyu teması: derin lacivert zemin (`#0b0f1a`) + güneş amberi vurgu
(`#f7b32b`). Logo: doğan güneş halkası + şimşek (SVG, `mobile/src/components/Brand.js`).
Tipografi: Space Grotesk (başlık/rakam) + Inter (gövde). Tüm belirteçler
`mobile/src/theme.js`'te (`colors`, `spacing`, `font`, `text`); grafik seri
renkleri renk körlüğü (CVD) validatöründen geçirilmiştir — değiştirilecekse
yeniden doğrulanmalıdır.

## Takım için kalan işler (Sprint 2–3)

- [ ] **VB:** LightGBM üretim modeli v1 (`production.py` gövdesi, kontrat sabit) — Sprint 2
- [ ] **VB:** LightGBM tüketim modeli v1 (`consumption.py` gövdesi) — Sprint 2
- [ ] **VB:** EPİAŞ şekil doğrulama raporu (METHOD §3) — Sprint 2
- [ ] **VB:** Model doğruluk raporu (nMAE, hold-out) — Sprint 3
- [ ] **YZ:** Gemini anahtarıyla uçtan uca agent testi + prompt incelemesi — Sprint 2
- [ ] **YZ-3:** Chroma semantik hafıza (opsiyonel, `memory.py` genişleme noktası) — Sprint 2
- [ ] **Ortak:** EPDK güncel tarife + mahsup bedeli teyidi (`config.py`) — teslim öncesi
- [ ] **Ortak:** Railway/Cloud Run canlı URL + EAS ile APK — Sprint 3
- [ ] **Ortak:** 3 dk demo videosu (akış: DEPLOY §6) — Sprint 3

## Veri kaynakları

[Open-Meteo](https://open-meteo.com) (canlı hava, anahtarsız) ·
[PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/) (ışınım geçmişi) ·
EPDK (tarife, koda gömülü, kaynaklı) · [EPİAŞ Şeffaflık](https://seffaflik.epias.com.tr)
(profil doğrulama) · UCI/London (tüketim şekli) · ETKB (emisyon faktörü)
