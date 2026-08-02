# Çalıştırma ve Production Yayını

## Canlı Sistem

- Web ve API: https://api.altspacelabs.com
- Sağlık kontrolü: https://api.altspacelabs.com/api/health
- Runtime: Railway üzerinde Docker
- Kalıcı veri: `/data/wattra.db` bağlı volume
- Yapay zeka: Gemini 3.6 Flash function-calling

Gemini ve JWT anahtarları yalnızca sunucu ortam değişkenlerinde tutulur; repoya,
web çıktısına veya mobil pakete eklenmez.

## Production Değişkenleri

```text
JWT_SECRET_KEY=<güçlü-rastgele-secret>
GEMINI_API_KEY=<secret>
GEMINI_MODEL=gemini-3.6-flash
WATTRA_DB=/data/wattra.db
WATTRA_CORS_ORIGINS=https://api.altspacelabs.com
WATTRA_ALLOWED_HOSTS=api.altspacelabs.com,*.up.railway.app,healthcheck.railway.app
WATTRA_ENABLE_DOCS=0
WATTRA_SEMANTIC_MEMORY=0
```

## Yerel Geliştirme

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest tests -q
ruff check .
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expo:

```powershell
cd mobile
npm ci
npm run doctor
npx expo start
```

## Railway Deploy

Kökteki `Dockerfile`, Expo Web çıktısını üretir ve FastAPI ile aynı image içinde
servis eder. Kökteki `railway.json`, `/api/health` endpoint'ini healthcheck olarak
kullanır.

```powershell
railway link
railway up --service wattra-api
python backend/scripts/smoke_deploy.py https://api.altspacelabs.com
```

SQLite volume düzenli yedeklenmelidir. Birden çok backend instance'ına geçildiğinde
veritabanı managed PostgreSQL'e taşınmalıdır.

## Mobil Build

```powershell
cd mobile
npm run doctor
npm run build:android:preview
npm run build:ios:preview
npm run build:ios:production
```

iOS production build için aktif Apple Developer Program üyeliği, App Store Connect
erişimi ve `com.wattra.energy` Bundle ID yetkisi gerekir. Apple parolası ve 2FA kodu
repoya veya `.env` dosyasına yazılmaz; EAS girişinde etkileşimli olarak kullanılır.

## Release Kontrolü

```powershell
Invoke-RestMethod https://api.altspacelabs.com/api/health
python backend/scripts/smoke_deploy.py https://api.altspacelabs.com
cd mobile
npm run doctor
npm run export:web
```

Gerçek cihazda kayıt, onboarding, ev konumu, plan, cihaz durumu, asistan, rapor,
ayarlar ve tekrar giriş akışları kontrol edilir. Tasarruf değerleri optimizer
simülasyonudur; sayaçtan ölçülmüş gerçekleşen kazanç olarak sunulmaz.
