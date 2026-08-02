# Çalıştırma ve Production Yayını

## Canlı Sistem

Wattra production ortamı kullanıcının bilgisayarından bağımsız çalışır.

- Web ve API: https://api.altspacelabs.com
- Railway servis URL'i: https://wattra-api-production.up.railway.app
- Sağlık kontrolü: https://api.altspacelabs.com/api/health
- Platform: Railway, Docker, `/data` kalıcı volume
- DNS/TLS: Cloudflare proxied CNAME ve Railway custom-domain sertifikası
- LLM: Gemini 3.6 Flash; anahtar yalnızca Railway secret olarak saklanır

Cloudflare Tunnel artık production trafiğinde kullanılmaz. Windows'taki eski
`Cloudflared` servisi devre dışıdır ve bilgisayar kapalıyken uygulama çalışmaya devam eder.

## Ortam Değişkenleri

Yerel entegrasyon değerleri repo kökündeki git-ignored `.env` dosyasındadır.
Şablon `.env.example` içinde bulunur. Production değerleri Railway Variables ekranında
tutulur; `.env`, API anahtarları ve tunnel token'ları commit edilmez.

Temel production değişkenleri:

```text
JWT_SECRET_KEY=<güçlü-rastgele-secret>
GEMINI_API_KEY=<secret>
GEMINI_MODEL=gemini-3.6-flash
WATTRA_DB=/data/wattra.db
WATTRA_CORS_ORIGINS=https://api.altspacelabs.com
WATTRA_ALLOWED_HOSTS=api.altspacelabs.com,*.up.railway.app,healthcheck.railway.app
WATTRA_ENABLE_DOCS=0
WATTRA_SEMANTIC_MEMORY=0
OLLAMA_ENABLED=0
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

Uygulamanın production API adresi `mobile/eas.json` ve `mobile/app.config.js`
tarafından belirlenir. Son kullanıcıya sunucu adresi veya altyapı ayarı gösterilmez.

## Railway Deploy

Repo kökündeki `Dockerfile`, Expo Web çıktısını üretip FastAPI ile aynı image içinde
servis eder. `railway.json` healthcheck'i `/api/health` endpoint'ine bağlar.

```powershell
railway link
railway up --service wattra-api
python backend/scripts/smoke_deploy.py https://api.altspacelabs.com
```

SQLite dosyası `/data/wattra.db` konumundadır. Volume silinirse kullanıcı verisi de
silinir; düzenli yedek ve sonraki production aşamasında managed PostgreSQL gerekir.

## Yerel PC Alternatifi

Railway arızasında yerel backend ve eski tunnel geçici olarak kullanılacaksa
Cloudflare DNS kaydı yeniden tunnel hedefine alınmalı ve `Cloudflared` Windows servisi
yeniden etkinleştirilmelidir. `START_HOST.cmd` yalnızca bu acil durum akışı içindir;
normal kullanımda çalıştırılmaz.

## Android APK

Son doğrulanan preview build:

- Build: https://expo.dev/accounts/isobed18/projects/wattra/builds/ef0686ec-ec06-4a82-8cd7-6ab817ff7e4a
- Yerel çıktı: `C:\Users\ishak\Downloads\Wattra-0.1.0-preview.apk`

Yeni build:

```powershell
cd mobile
npm run doctor
npm run build:android:preview
```

## iOS TestFlight

Apple parolası veya 2FA kodu repoya ya da `.env` dosyasına yazılmaz. Apple Developer
hesabı sahibi aşağıdaki komutu etkileşimli çalıştırır; EAS dağıtım sertifikasını ve
provisioning profile'ı oluşturur, ardından build'i TestFlight'a gönderir.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-ios-testflight.ps1
```

Gerekli hesap tarafı:

- Aktif Apple Developer Program üyeliği
- Bundle ID: `com.wattra.energy`
- Apple ID ile giriş ve 2FA onayı
- App Store Connect'te sözleşme/vergisel engel bulunmaması

## Release Kontrolü

```powershell
Invoke-RestMethod https://api.altspacelabs.com/api/health
python backend/scripts/smoke_deploy.py https://api.altspacelabs.com
cd mobile
npm run doctor
npm run export:web
```

Gerçek cihazda kayıt, onboarding, konum, plan, cihaz durumu, asistan, rapor,
ayarlar ve tekrar giriş akışları kontrol edilir. Tasarruf değerleri optimizasyon
simülasyonudur; sayaçtan ölçülmüş gerçekleşen kazanç olarak sunulmaz.
