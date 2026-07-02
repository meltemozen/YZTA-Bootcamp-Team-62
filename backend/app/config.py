"""Voltaic yapılandırması — TÜM enerji sabitleri ve kaynakları BURADADIR.

Kod içinde başka yerde fiyat/faktör sabiti YOKTUR. Her değerin yanında
kaynağı ve tarihi yazar; EPDK kurul kararı sonrası (genelde Ocak/Nisan/Temmuz)
bu dosya güncellenir ve docs/METHOD.md'deki tarih işlenir.

── MEVZUAT ÖZETİ (Temmuz 2026 itibarıyla) ─────────────────────────────────────
* Mesken tek zamanlı tarife KADEMELİDİR: aylık 240 kWh'e kadar düşük,
  üstü yüksek kademe (EPDK, 4 Nisan 2026 tarife tablosu).
* Üç zamanlı tarifede kademe UYGULANMAZ. Dilimler tüm Türkiye'de sabittir:
  gündüz 06-17, puant 17-22, gece 22-06.
* MAHSUPLAŞMA SAATLİKTİR: 2 Nisan 2026 RG ile aylık mahsup kalktı,
  1 Mayıs 2026'dan itibaren üretim-tüketim SAAT bazında netleşir. Saat içi
  fazla üretim şebekeye verilir ve dağıtım bedeli/vergiler DÜŞÜLMÜŞ fiyattan
  (yaklaşık perakende fiyatın %70'i) satın alınır. Bu yüzden öz tüketim her
  saatte satıştan kârlıdır — optimizasyonun ekonomik temeli budur.
* Mesken çatı GES mahsuplaşma üst sınırı 10 kW'tır.
"""

import os

# --- LLM ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- Veritabanı ---
DB_PATH = os.getenv("VOLTAIC_DB", os.path.join(os.path.dirname(__file__), "..", "voltaic.db"))

# --- EPDK tarife (vergiler DAHİL son kullanıcı fiyatı, TL/kWh) ---
# Kaynak: EPDK 4 Nisan 2026 tarife tablosu; sektör derlemeleri (Haziran 2026).
# Üç zamanlı KDV-hariç taban: gündüz 4.38, puant 6.17, gece 2.94
# → vergiler (KDV %20 + BTV + Enerji Fonu) ile ≈ ×1.27.
TARIFE = {
    "mesken": {
        # Kademeli tek zamanlı: aylık eşik ve iki fiyat
        "kademe_esik_kwh_ay": 240,
        "tek_zamanli_dusuk": 3.24,
        "tek_zamanli_yuksek": 4.86,
        "uc_zamanli": {"gunduz": 5.57, "puant": 7.85, "gece": 3.74},
    },
    "isyeri": {
        # Ticarethane: kademe eşiği günlük 30 kWh ≈ aylık 900 kWh
        "kademe_esik_kwh_ay": 900,
        "tek_zamanli_dusuk": 4.45,
        "tek_zamanli_yuksek": 5.15,
        # Ticarethane üç zamanlı — YAKLAŞIK (bölge dağıtım bedeliyle oynar),
        # teslim öncesi görevli tedarik şirketi tablosuyla doğrulanacak.
        "uc_zamanli": {"gunduz": 5.80, "puant": 8.20, "gece": 3.90},
    },
}

# Saatlik mahsuplaşmada fazla enerjinin satış fiyatı = o saatin perakende
# fiyatı − dağıtım bedeli − vergiler ≈ perakende × bu oran.
# (Sektör örneği: mesken ~3.5 TL/kWh satış ↔ ~4.86 alış → ≈0.72)
MAHSUP_SATIS_ORANI = 0.70

# Mesken çatı GES mahsuplaşma sınırı (Lisanssız Üretim Yönetmeliği)
MESKEN_MAHSUP_LIMIT_KW = 10.0

SAAT_DILIMLERI = {"gunduz": range(6, 17), "puant": range(17, 22), "gece": list(range(22, 24)) + list(range(0, 6))}

# --- PV üretim modeli (v0 fiziksel model) ---
PV_PERFORMANS_ORANI = 0.80      # kablolama, inverter, kir kayıpları
PV_SICAKLIK_KATSAYISI = 0.004   # güç kaybı / °C (25°C üstü hücre sıcaklığı)
PV_NOCT_FAKTORU = 0.03          # hücre sıcaklığı ≈ hava + 0.03 × ışınım

# --- Karbon ve çevresel eşdeğerler ---
# TR şebeke emisyon faktörü — ETKB "Türkiye Ulusal Elektrik Şebekesi Emisyon
# Faktörü Bilgi Formu" (rev. 03.2024): üretim EF ≈ 0.434-0.439 tCO2e/MWh.
CO2_KG_PER_KWH = 0.44
# Olgun bir ağacın yıllık CO2 emilimi (EPA / One Tree Planted ort. değeri)
AGAC_KG_CO2_YIL = 22.0
# Ortalama binek araç emisyonu (TR filo ortalaması yaklaşımı, kg CO2/km)
ARABA_KG_CO2_KM = 0.17

# --- Belirsizlik ---
# Tüketim profili fatura kalibrasyonuna dayandığı için TL tasarrufları
# kullanıcıya tek rakam değil aralık olarak gösterilir.
TASARRUF_BELIRSIZLIK = 0.25  # ±%25
