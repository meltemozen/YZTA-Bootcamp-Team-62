# Teknik Dokümantasyon

> Kod dili İngilizce (dosya/metot/alan adları); açıklama ve mobil arayüz
> Türkçe. Kontrat: [CONTRACT.md](CONTRACT.md).

## Mimari

```
Open-Meteo ─┐                          ┌─ get_weather
PVGIS ──────┤   ML Model Katmanı (VB)  ├─ forecast_production  (LightGBM)
EPDK tarife ┤   + kural motorları      ├─ forecast_consumption (fatura kalibrasyonu)
Fatura ─────┘                          ├─ get_tariff           (kademe + saatlik mahsup)
                                       ├─ optimize             (deterministik plan)
                                       └─ read_memory/write_memory  (SQLite)
                        │ tool'lar
                        ▼
        Gemini Agent (function-calling döngüsü, YZ)
        · kendi kararıyla tool çağırır · itiraza yeniden planlar
        · grounding guard ile araç çıktılarının dışına çıkamaz
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
| `backend/app/agent/` | Gemini orchestrator + context + grounding guard | YZ |
| `backend/app/services/` | Ay sonu raporu (report), proaktif bildirim (notifications) | YZ |
| `backend/tests/` | Agent, API, auth, model ve servis testleri | Ortak |
| `mobile/` | Expo uygulaması — Android, iOS ve web | YZ-3 |
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

Testler: `cd backend && python -m pytest tests/ -v` (ağ gerektirmez).
Ayrıntılı çalıştırma/deploy: [DEPLOY.md](DEPLOY.md)

## Tasarım kimliği

"Gece şebekesi" koyu teması: derin lacivert zemin (`#0b0f1a`) + güneş amberi vurgu
(`#f7b32b`). Logo: doğan güneş halkası + şimşek (SVG, `mobile/src/components/Brand.js`).
Tipografi: Space Grotesk (başlık/rakam) + Inter (gövde). Tüm belirteçler
`mobile/src/theme.js`'te (`colors`, `spacing`, `font`, `text`); grafik seri
renkleri renk körlüğü (CVD) validatöründen geçirilmiştir — değiştirilecekse
yeniden doğrulanmalıdır.

## Production Durumu

- LightGBM üretim artifact'i image içine dahil edilir ve runtime'da zorunludur.
- Tüketim modeli aylık fatura ile haneye kalibre edilir.
- Hava girdisi Open-Meteo'dan anlık ve saatlik tahmin olarak alınır.
- Gemini function-calling yalnızca sunucuda çalışır; mobil pakette API anahtarı yoktur.
- Android APK ve birleşik Expo Web + FastAPI image üretim akışları hazırdır.

## Veri kaynakları

[Open-Meteo](https://open-meteo.com) (canlı hava, anahtarsız) ·
[PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/) (ışınım geçmişi) ·
Kullanıcı tanımlı tarife override'ı + kaynaklı sabit tarife tablosu · [EPİAŞ Şeffaflık](https://seffaflik.epias.com.tr)
(profil doğrulama) · UCI/London (tüketim şekli) · ETKB (emisyon faktörü)
