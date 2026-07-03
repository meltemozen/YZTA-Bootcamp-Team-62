# Sprint 1 — Board

**Sprint hedefi:** Uçtan uca çalışan ürün + kilitli model–agent kontratı + temiz
İngilizce kod tabanı. **45 SP / 45 tamamlandı.**

## Board görüntüsü

> Hafta sonu toplantısında güncel board'un ekran görüntüsü buraya eklenecek
> (`board.png`). Aşağıdaki tablo board'un metin karşılığıdır.

## Kart → durum (Done)

| Kart | Ekip | SP | Kod karşılığı |
|---|---|---|---|
| S1-1 Repo & altyapı + İngilizce refactor | YZ | 5 | tüm depo, `docs/`, klasör mimarisi |
| S1-2 Model–Agent kontratı KİLİTLE | Ortak | 3 | `backend/app/schemas.py`, `docs/CONTRACT.md` |
| S1-3 Veri boru hattı (PVGIS+Open-Meteo) | VB | 5 | `data/scripts/pvgis_fetch.py`, `tools/weather.py` |
| S1-4 Backend FastAPI+Docker+SQLite | YZ | 3 | `backend/app/main.py`, `db.py`, `Dockerfile` |
| S1-5 6 tool + optimizasyon motoru | VB+YZ | 8 | `backend/app/tools/*` |
| S1-6 Gemini agent + fallback + müzakere | YZ | 8 | `backend/app/agent/*` |
| S1-7 Mobil + web (Expo, 5 ekran) | YZ | 8 | `mobile/*` |
| S1-8 Uyarı + karşı-olgusal rapor + CO₂ + testler | Ortak | 5 | `services/*`, `backend/tests/*` |

## Sütun sayıları (sprint sonu)

`Product Backlog: 0 (S1 kapsamı)` · `Todo: 0` · `In Progress: 0` · `In Review: 0`
· `Done: 8 / 8`

> **Not (board temizliği):** Trello'daki eski kartlar orijinal PDF planından birebir
> kopyalanmıştı ve yapılan işle birebir örtüşmüyordu (ör. "LangGraph agent" yerine
> **Gemini function-calling** kuruldu; JSON şema kontratı ayrı kart değildi). Board,
> gerçekte teslim edilen işe göre yukarıdaki 8 karta sadeleştirildi.
