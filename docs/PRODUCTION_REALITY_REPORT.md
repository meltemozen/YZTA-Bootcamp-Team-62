# Production Reality Report

Bu raporun amacı projedeki iddiayı netleştirmek: şu an sistem gerçekten ne
yapıyor, nerede eğitilmiş model var, nerede demo/fallback/synthetic veri var ve
production'a geçmeden önce hangi parçalar temizlenmeli.

## Kısa karar

Sistem şu anda "tamamen mock" değil. Canlı çalışan bir optimizasyon hattı var:
kullanıcı profili alınır, Open-Meteo'dan saatlik hava/ışınım çekilir, PV üretimi
tahmin edilir, fatura bazlı tüketim profili çıkarılır, Türkiye tarife tablosuyla
cihaz/batarya planı optimize edilir ve mobil uygulama bunu API'den gösterir.

Ama sistem şu haliyle production-ready de değil. En büyük açıklar:

- Tüketim tarafı gerçek kullanıcı sayaç verisiyle öğrenmiyor; aylık fatura kWh'i
  ile ölçeklenen generic load-shape kullanıyor.
- Cihaz tüketimleri katalog varsayımı; kullanıcıya düzenletiliyor ama ölçülmüş
  cihaz profili yok.
- Aylık rapordaki "gerçekleşen tasarruf" sayaçtan ölçülen gerçek veri değil;
  kullanıcının "uyguladım" feedback'i üzerinden simülasyon.
- Hava servisi çökünce cache/synthetic fallback var; ürün demo için durmuyor ama
  production'da bu kalite etiketi kullanıcıya/API'ye daha sert taşınmalı.
- Eğitim ham verileri repo'da yok; script ve artefact var ama birebir yeniden
  üretilebilir veri sürümleme zinciri eksik.

## Gerçek çalışan parçalar

### 1. Canlı hava ve ışınım girdisi

Kod: `backend/app/tools/weather.py`

Sistem Open-Meteo forecast endpoint'inden şu saatlik girdileri çekiyor:

- `shortwave_radiation`
- `temperature_2m`
- `cloud_cover`
- current weather değerleri

Bugün için çağrıldığında mevcut saatin gerçek/current değerlerini forecast
dizisinin içine işliyor. Bu iyi bir nokta: sistem sadece "yarın hava tahmini"
değil, bugünkü anlık değişimi de üretim tahminine katabiliyor.

Sınırlama: endpoint hata verirse önce cache, o da yoksa seasonal synthetic profil
üretiliyor. Bu demo için mantıklı; production'da synthetic sonuçların normal
tahmin gibi görünmemesi gerekir.

### 2. PV üretim tahmini

Kod:

- `backend/app/tools/production.py`
- `backend/app/models/production_v1_lgbm.txt`
- `backend/app/models/production_v1.json`
- `data/scripts/train_production_model_lgbm.py`
- `data/scripts/compare_production_models.py`

Burada gerçek bir model artefact'i var. Runtime aktif model:

- model tipi: LightGBM
- versiyon: `v1-lightgbm`
- artefact: `backend/app/models/production_v1_lgbm.txt`
- girdiler: ışınım, sıcaklık, bulut etkileşimi, edge-hour loss, panel kW
- hedef: saatlik AC kWh / kWp

Araştırma raporundaki sonuç:

| Model | nMAE |
|---|---:|
| LightGBM | 2.08% |
| XGBoost | 2.09% |
| RandomForest | 2.13% |
| Ridge | 3.60% |
| physical baseline | 5.47% |

Yani üretim tarafında "bir şey eğitilmiş mi?" sorusunun cevabı evet. LightGBM
artefact'i backend'e gömülmüş durumda ve API canlı olarak bunu kullanıyor.

Sınırlama: Ham eğitim dosyaları (`data/raw/pvgis_hourly.csv`,
`data/raw/open_meteo_hourly.csv`) repo'da yok. Bu normal olabilir çünkü büyük CSV
commitlenmez; ama production'a geçişte DVC/S3/Drive linki/hash ile veri versiyonu
kanıtlanmalı.

### 3. Tüketim tahmini

Kod:

- `backend/app/tools/consumption.py`
- `backend/app/models/consumption_v1.json`
- `data/scripts/train_consumption_model.py`
- `data/scripts/evaluate_advanced_consumption.py`

Runtime şu anda CatBoost binary model çalıştırmıyor. CatBoost ile bir tüketim
şekli çıkarılmış ve distillation yaklaşımıyla JSON'a gömülmüş:

- versiyon: `v2-catboost-calibrated`
- runtime artefact: `consumption_v1.json`
- girdiler: kullanıcı tipi, tarih, aylık fatura kWh, esnek cihazlar
- çıktı: 24 saatlik base-load tahmini

Burada doğru ifade şu olmalı:

> "Tüketim tarafında canlı inference yapan ağır ML modeli yok; CatBoost ile
> öğrenilmiş generic saatlik profil backend'de hafif JSON olarak kullanılıyor."

Bu production için dürüst bir yaklaşım olabilir ama ürün iddiası "maliyet düşürme"
ise yeterli değil. Gerçek sayaç geçmişi, cihaz bazlı tüketim veya kullanıcı
feedback'iyle online kalibrasyon olmadan hane özelinde kesin tasarruf iddiası
kurulamaz. Bu yüzden UI'da tasarruf aralığı gösterilmesi doğru.

### 4. Türkiye tarife adaptörü

Kod:

- `backend/app/tools/tariff.py`
- `backend/app/config.py`

Sistem Türkiye için iki tarife modunu hesaplıyor:

- tek zamanlı, kademeli mesken/ticarethane fiyatı
- üç zamanlı: gündüz, puant, gece

Ayrıca saatlik mahsuplaşmayı maliyet fonksiyonuna dahil ediyor: alış fiyatı ile
şebekeye satış fiyatı ayrı tutuluyor. Bu ürünün ekonomik mantığı için değerli.

Sınırlama: Fiyatlar config içinde sabit tablo. Production'da EPDK/supplier
tarifeleri için güncelleme prosedürü, kaynak linki, geçerlilik tarihi ve otomatik
test gerekir.

### 5. Optimizasyon motoru

Kod: `backend/app/tools/optimize.py`

Bu kısım mock değil; deterministik bir maliyet optimizasyonu çalışıyor.

Yaptıkları:

- saatlik net yük = tüketim - üretim
- ithal elektrik alış fiyatı ile, fazla üretim satış fiyatı ile değerleniyor
- cihazlar maliyeti en düşüren saatlere yerleştiriliyor
- EV/pompa gibi interruptible cihazlar parçalı çalışabiliyor
- EV için fiziksel süre kontrolü var: `duration >= ceil(kWh / power_kw)`
- bugün planında geçmiş saatler otomatik bloklanıyor
- batarya varsa güneş fazlasında şarj, pahalı ithalat saatlerinde deşarj ediyor
- greedy + coordinate descent ile çoklu cihaz çakışmaları tekrar iyileştiriliyor

Bu proje açısından en gerçek ürün çekirdeği burası. Mock açıklama değil, gerçek
maliyet fonksiyonu var.

Sınırlama: Optimizasyon mixed-integer solver kullanmıyor. 24 saatlik küçük problem
için mevcut yaklaşım yeterli olabilir, ama production iddiası büyürse OR-Tools/Pyomo
tabanlı constraint optimizer daha doğru olur.

### 6. Mobil uygulama

Kod:

- `mobile/src/screens/Onboarding.js`
- `mobile/src/screens/Today.js`
- `mobile/src/screens/Report.js`
- `mobile/src/api.js`

Mobil uygulama gerçek backend API'sini çağırıyor:

- onboarding profili kaydediyor
- konum izni alıp koordinatı weather-check'e gönderiyor
- Today ekranında `/api/plan/{id}` çağrılıyor
- Report ekranında `/api/report/{id}` çağrılıyor
- Assistant ekranında `/api/assistant` çağrılıyor

Mock ekran yok; ama default değerler var:

- varsayılan şehir: İzmir
- varsayılan panel: 5 kW
- varsayılan fatura: 300 kWh/ay
- default API URL: Expo test kolaylığı için yerel ağ adresi

Bu default'lar "mock veri" gibi görünebilir. Production'da kullanıcı seçim yapmadan
varsayılanın sessizce gerçek profil gibi kaydedilmesini engellemek gerekir.

## Mock / fallback / synthetic görünen yerler

### Bilinçli fallback olanlar

- `weather.py`: Open-Meteo yoksa cache/synthetic.
- `production.py`: LightGBM yoksa physical/linear fallback.
- `orchestrator.py`: Gemini/Ollama yoksa deterministic fallback.
- `memory.py`: semantic memory yoksa keyword fallback.

Bunlar "saçma mock" değil; dayanıklılık katmanı. Ama production'da her fallback
cevabın veri kalite etiketiyle görünmesi gerekir.

### Gerçek production verisi olmayanlar

- `consumption_v1.json`: hane özelinde ölçülmüş veri değil, generic load-shape.
- `devices.json`: cihaz tüketimleri kaynaklı varsayım; ölçülmüş cihaz datası değil.
- `report.py`: gerçekleşen tasarruf sayaç verisi değil, kullanıcı feedback'i + simülasyon.
- `config.py` tarife değerleri: sabit tablo; otomatik güncelleme veya doğrulama yok.
- `data/raw/`: eğitim verisi repo'da yok; artefact'in veri lineage'ı eksik.

## "Gerçekten eğitilmiş mi?" cevabı

Evet, ama iki ayrı seviye var:

1. PV üretim modeli gerçekten eğitilmiş ve backend'de çalışan LightGBM artefact'i
   var. Bu taraf en güçlü ML parçası.
2. Tüketim tarafında CatBoost araştırması yapılmış, fakat production runtime'da
   CatBoost model çalışmıyor. CatBoost'tan çıkarılmış 24 saatlik profil JSON olarak
   kullanılıyor. Bu "distilled model" sayılır, ama hane özelinde öğrenen model
   değildir.

## Production'a geçmeden önce yapılması gerekenler

### P0 - Dürüstlük ve veri kalitesi

- API response'larına `weather_source`, `production_model_version`,
  `consumption_model_version`, `tariff_source`, `data_quality` alanlarını açıkça ekle.
- Synthetic/cached veri varsa UI'da bunu saklama; "canlı veri yok, tahmin kalitesi düşük"
  etiketi göster.
- "Gerçekleşen tasarruf" metnini değiştir: sayaç entegrasyonu yoksa "uygulanan öneri
  simülasyonu" denmeli.
- Varsayılan onboarding değerleriyle kayıt olmayı engelle veya kullanıcıya açık
  doğrulama yaptır.

### P1 - Tüketim modelini gerçek ürüne yaklaştırma

- Kullanıcıdan son 12 ay fatura kWh'i veya e-Devlet/dağıtım şirketi CSV import'u al.
- Plan uygulandı/uygulanmadı feedback'ini sadece rapor için değil, model kalibrasyonu
  için kullan.
- Cihaz bazlı `kWh`, `duration`, `earliest/latest`, `power_kw` değerlerini kullanıcı
  düzenleyebilsin.
- Zamanla öğrenen kişisel load-shape ekle: generic shape + user calibration + feedback.

### P2 - Optimizasyonu production seviyesine çekme

- Mevcut greedy+coordinate descent küçük problem için hızlı; ama kurallar artınca
  OR-Tools CP-SAT veya linear programming solver eklenmeli.
- Kısıtlar genişletilmeli: cihaz önceliği, deadline, minimum çalışma blokları,
  konfor sıcaklığı, EV hedef SOC, batarya min/max SOC, inverter gücü, şebeke limitleri.
- Savings hesabı için baseline/habit model daha iyi öğrenilmeli; şu an referans saat
  kabulleri var.

### P3 - Türkiye entegrasyonu

- EPDK tarifeleri kaynak linki ve geçerlilik tarihiyle ayrı veri dosyasına alınmalı.
- Tarife güncellemesi için test yazılmalı: üç zamanlı saatler, kademe sınırı,
  mahsuplaşma oranı.
- Ticarethane fiyatları "approximate" kalmamalı; supplier/abone grubu bazlı net tablo
  kullanılmalı.

### P4 - ML reproducibility

- Ham veri repo'ya commitlenmese bile DVC/S3/Drive ile versiyonlanmalı.
- Model artefact manifest'ine şunlar eklenmeli:
  - training data hash
  - script commit sha
  - train/test tarih aralığı
  - metrikler
  - model parametreleri
  - generated_at
- CI'da küçük fixture dataset ile train script smoke test çalışmalı.

## Son söz

Şu an ürünün gerçek iddiası şöyle yazılmalı:

> Wattra, konum bazlı canlı hava/ışınım verisi ve Türkiye tarife kurallarıyla,
> kullanıcının panel gücü, fatura tüketimi ve esnek cihazlarını dikkate alarak
> günlük cihaz/batarya çalışma planı önerir. PV üretim tahmini eğitilmiş LightGBM
> modeliyle yapılır. Tüketim tahmini şu an kişisel sayaç verisi değil, fatura ile
> kalibre edilen generic load-shape modelidir; bu yüzden tasarruflar aralık olarak
> verilir ve sayaçtan ölçülmüş gerçekleşme iddiası kurulmaz.

Bu cümle hem güçlü hem dürüst. Production'a geçişin ana işi de bu dürüst MVP'yi
gerçek kullanıcı verisi, veri kalite etiketleri ve daha güçlü kişisel tüketim
kalibrasyonuyla sertleştirmek olmalı.
