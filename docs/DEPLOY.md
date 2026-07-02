# Çalıştırma ve Yayına Alma

## 1. Backend — yerelde (geliştirme)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows | Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # GEMINI_API_KEY'i içine yaz
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API dokümanı: http://localhost:8000/docs (FastAPI otomatik)
- Sağlık: `GET /api/saglik` → `{"agent": "gemini"}` görüyorsanız anahtar tanınmış demektir.
- Testler: `python -m pytest tests/ -v` (12 test, ağ gerektirmez)

> **GEMINI_API_KEY olmadan da çalışır** — agent kural tabanlı fallback moduna
> düşer ve yanıtlarda `agent_modu: "fallback"` görünür. Anahtar:
> https://aistudio.google.com/apikey (ücretsiz katman yeterli).

## 2. Mobil — Expo Go ile telefonda (demo yolu)

```bash
cd mobile
npm install
npx expo start
```

1. Telefona **Expo Go** uygulamasını kur (Play Store / App Store).
2. Terminaldeki QR kodu okut.
3. Telefon ve bilgisayar **aynı Wi-Fi'da** olmalı; uygulamada
   Ayarlar → Sunucu adresi'ne bilgisayarın yerel IP'sini yaz:
   `http://192.168.1.XX:8000` (IP'yi `ipconfig` ile bulun).
   İlk kurulumda backend'e ulaşamazsa Onboarding bağlantı uyarısı verir.

## 2b. Web sitesi — aynı kod tabanı, tarayıcıda

Ayrı bir web projesi YOKTUR: Expo uygulaması react-native-web ile tarayıcıya
derlenir. FastAPI yalnızca JSON API'dir; web sitesi statik dosyadır.

```bash
cd mobile
npx expo start --web          # geliştirme: http://localhost:8081
# veya üretim derlemesi:
npx expo export --platform web    # → dist/ klasörü (statik)
python -m http.server 3000 --directory dist
```

Statik `dist/` klasörü Netlify/Vercel/GitHub Pages'e olduğu gibi yüklenebilir;
tek koşul backend URL'inin erişilebilir olması (Ayarlar ekranından değiştirilebilir,
web'de varsayılan: sayfanın açıldığı makinede :8000).

## 3. Backend — Docker ile

```bash
docker compose up --build
# GEMINI_API_KEY ortam değişkeni compose'a geçer:
# GEMINI_API_KEY=xxx docker compose up --build
```

## 4. Canlıya alma (ücretsiz katman)

**Railway / Render (önerilen, 10 dk):**
1. GitHub repo'yu bağla, kök dizin `backend/`, Dockerfile otomatik algılanır.
2. Ortam değişkeni `GEMINI_API_KEY` ekle; volume → `/data` (SQLite kalıcılığı).
3. Çıkan URL'i `mobile/app.json` → `extra.apiUrl`'e yaz.

**Google Cloud Run (bootcamp anlatısına uygun):**
```bash
gcloud run deploy voltaic-api --source backend/ \
  --region europe-west1 --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY
```
Not: Cloud Run dosya sistemi kalıcı değildir — teslim demosu için yeterli,
gerçek kullanıcı için Railway volume veya Cloud SQL'e geçin.

## 5. Mobil — kurulabilir APK (jüri demosu için)

```bash
npm install -g eas-cli
eas login                          # ücretsiz Expo hesabı
cd mobile
eas build -p android --profile preview
```
Çıkan APK linkini telefona kur — "gerçek uygulama" demosu.
`app.json` → `extra.apiUrl` canlı backend URL'ine işaret etmeli.

## 6. Demo videosu akış önerisi (3 dk)

1. (0:00) Problem: fatura + "paneli var ama ne zaman çalıştıracağını bilmiyor".
2. (0:30) Onboarding: 4 adımda kurulum, telefonda.
3. (1:00) Bugün ekranı: plan kartları + grafik; "neden 13:00?" → gerekçe.
4. (1:30) Asistan: "salı öğlen evde yokum" → plan değişiyor, tool zinciri görünür
   (hafiza_yaz → optimize). **Agent kanıtı bu sahne.**
5. (2:15) Proaktif bildirim + Ay sonu raporu (karşı-olgusal + CO₂).
6. (2:45) Mimari tek slayt: 2 ML model + Gemini agent + mobil.
