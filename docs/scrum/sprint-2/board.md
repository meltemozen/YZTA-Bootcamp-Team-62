# Sprint 2 — Board

**Sprint hedefi:** Tahmin motorunu v1 model artifact'leriyle güçlendirmek ve planı
kullanıcının gerçek konumu + anlık/gelecek hava tahminiyle üretmek.

## Bu branch'te yapılan işler

| Kart | Ekip | SP | Durum | Kod karşılığı |
|---|---|---:|---|---|
| S2-1 Weather-aware üretim modeli v1 | VB | 8 | Branch'te | `backend/app/tools/production.py`, `backend/app/models/production_v1.json`, `data/scripts/train_production_model.py` |
| S2-2 Generic smart-meter tüketim modeli v1 | VB | 8 | Branch'te | `backend/app/tools/consumption.py`, `backend/app/models/consumption_v1.json`, `data/scripts/train_consumption_model.py` |
| S2-4 Gemini/Ollama provider zinciri | YZ | 5 | Branch'te | `backend/app/agent/orchestrator.py`, `backend/app/agent/local_llm.py`, `backend/app/config.py` |
| S2-6 Cihaz kataloğu + EV şarj metadata'sı | YZ | 3 | Branch'te | `backend/app/data/devices.json`, `backend/app/tools/optimize.py`, `docs/research/DEVICE_AND_EV_ASSUMPTIONS.md` |
| S2-7 Expo konum izni + hava kontrolü | YZ | 5 | Branch'te | `mobile/src/screens/Onboarding.js`, `mobile/src/api.js`, `backend/app/main.py` |
| S2-8 Gerçek zamanlı optimizer + performans | YZ | 5 | Branch'te | `backend/app/tools/weather.py`, `backend/app/tools/optimize.py`, `backend/app/tools/tariff.py`, `docs/research/ENERGY_OPTIMIZATION_RESEARCH.md` |

## Notlar

- Çalışma branch'i: `ml/s2-weather-local-llm`.
- Model yaklaşımı LightGBM'e kilitlenmedi. Öncelik doğru runtime girdileri:
  konum, bugün/yarın hava tahmini, ışınım, sıcaklık, bulut ve fatura kalibrasyonu.
- Üretim modeli PVGIS CSV ile yeniden eğitilebilir. Tüketim modeli açık smart-meter
  CSV'lerinden saatlik şekil çıkarıp kullanıcının faturasıyla ölçekler.
- Plan her çağrıda yeniden optimize edilir; bugünün geçmiş saatleri cihaz ve batarya
  dispatch için otomatik bloklanır.
