# Teknik Dokümantasyon

## Mimari

```
Open-Meteo ─┐                          ┌─ hava_getir
PVGIS ──────┤   ML Model Katmanı (VB)  ├─ uretim_tahmin   (v0 fiziksel → v1 LightGBM)
EPDK tarife ┤   + kural motorları      ├─ tuketim_tahmin  (fatura kalibrasyonu)
Fatura ─────┘                          ├─ tarife_getir    (kademe + saatlik mahsup)
                                       ├─ optimize        (deterministik plan)
                                       └─ hafiza_oku/yaz  (SQLite)
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
| `backend/app/schemas.py` | **Model–agent kontratı (KİLİTLİ, v1.1)** | Ortak |
| `backend/app/tools/` | 6 tool: hava, üretim, tüketim, tarife, optimize, hafıza | VB+YZ |
| `backend/app/agent/` | Gemini orkestratörü + fallback | YZ |
| `backend/app/services/` | Ay sonu raporu, proaktif bildirim | YZ |
| `backend/tests/` | 14 çekirdek + API testi | Ortak |
| `mobile/` | Expo uygulaması (5 ekran + grafik) — mobil ve web | YZ-3 |
| `data/scripts/` | PVGIS eğitim verisi çekme | VB |
| `docs/` | CONTRACT · METHOD · DEPLOY · TEKNIK | Ortak |

## Hızlı başlangıç

```bash
# Backend
cd backend && python -m venv .venv && .venv\Scripts\pip install -r requirements.txt
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
(`#f7b32b`). Logo: doğan güneş halkası + şimşek (SVG, `mobile/src/components/Marka.js`).
Tipografi: Space Grotesk (başlık/rakam) + Inter (gövde). Tüm belirteçler
`mobile/src/theme.js`'te; grafik seri renkleri renk körlüğü (CVD) validatöründen
geçirilmiştir — değiştirilecekse yeniden doğrulanmalıdır.

## Takım için kalan işler

- [ ] **VB:** LightGBM üretim modeli v1 (`uretim.py` gövdesi, kontrat sabit) — Sprint 2
- [ ] **VB:** EPİAŞ şekil doğrulama raporu (METHOD §3) — Sprint 2
- [ ] **YZ:** Gemini anahtarıyla uçtan uca agent testi + prompt incelemesi — Sprint 2
- [ ] **YZ-3:** Chroma semantik hafıza (opsiyonel, `hafiza.py` genişleme noktası) — Sprint 3
- [ ] **Ortak:** EPDK güncel tarife + mahsup bedeli teyidi (`config.py`) — teslim öncesi
- [ ] **Ortak:** Railway/Cloud Run canlı URL + EAS ile APK — Sprint 3
- [ ] **Ortak:** 3 dk demo videosu (akış: DEPLOY §6) — Sprint 3

## Veri kaynakları

[Open-Meteo](https://open-meteo.com) (canlı hava, anahtarsız) ·
[PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/) (ışınım geçmişi) ·
EPDK (tarife, koda gömülü, kaynaklı) · [EPİAŞ Şeffaflık](https://seffaflik.epias.com.tr)
(profil doğrulama) · UCI/London (tüketim şekli) · ETKB (emisyon faktörü)
