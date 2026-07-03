# Yöntem ve Veri Doğruluğu

> Bu doküman jürinin (ve kullanıcının) "rakamlarınız neye dayanıyor?" sorusunun
> cevabıdır. İlkemiz: **kararın yönünü sağlam veriye dayandır, TL rakamını
> dürüst aralıkla söyle.** Son mevzuat/fiyat doğrulaması: **3 Temmuz 2026.**

## 1. Katman katman doğruluk

| Katman | Kaynak | Doğruluk | Not |
|---|---|---|---|
| Güneş üretimi | Open-Meteo (canlı) + PVGIS (eğitim) | günlük ±%10-15 | En sağlam katman |
| Tarife | EPDK 4 Nisan 2026 tablosu | kesin | Kademeli mesken dahil |
| Mahsuplaşma | RG 02.04.2026 — **saatlik mahsup** | kesin kural | Satış ≈ alış×0.70 |
| Tüketim profili | Fatura kalibrasyonu + profil şekli | ±%20-30 | En zayıf katman |

**Kritik tasarım kararı:** "Çamaşırı 13:00'te at" önerisinin YÖNÜ üretim tahmini +
tarifeden çıkar (ikisi de sağlam). Tüketim hatası yalnızca gösterilen TL rakamını
etkiler → tüm tasarruflar **aralık** olarak gösterilir (±%25).

## 2. Üretim modeli

**v0 (çalışıyor):** fiziksel model —
`P = (GHI/1000) × kWp × PR(0.80) × sıcaklık_düzeltmesi`, hücre sıcaklığı
`T_hücre = T_hava + 0.03 × GHI`, 25°C üstü her derece %0.4 kayıp.

**v1 (VB ekibi):** LightGBM; eğitim verisi `data/scripts/pvgis_fetch.py`.
Değerlendirme: son yıl hold-out, nMAE; v0 baseline'ı geçemeyen model üretime alınmaz.

## 3. Tüketim modeli ve kalibrasyon

Türkiye'de hane saatlik tüketim verisi kullanıcıya açık değildir. Bu yüzden:
1. **Şekil:** UCI/London profillerinden türetilmiş normalize saatlik şekil,
   TR akşam piki belirginleştirilmiş; işyeri için mesai şekli.
2. **Ölçek:** aylık fatura kWh → günlük kWh.
3. **Mevsim düzeltmesi:** ±%10-15 sinüs.
4. **Doğrulama (VB görevi):** EPİAŞ bölgesel tüketim eğrisiyle şekil
   korelasyonu — Sprint 2 çıktısı.

## 4. Tarife ve mahsuplaşma — GÜNCEL MEVZUAT (Temmuz 2026)

Tüm değerler `backend/app/config.py`'de tek noktadan yönetilir.

**Kademeli tarife (tek zamanlı):** Mesken aylık **240 kWh** eşiği: altı ~3.24,
üstü ~4.86 TL/kWh (vergiler dahil, Haziran 2026). Ticarethane eşiği günlük
30 kWh (~900/ay). Uygulama, kullanıcının fatura kWh'inden **marjinal kademe
fiyatını** seçer. Üç zamanlıda kademe yoktur; dilimler: gündüz 06-17, puant
17-22, gece 22-06 (2026-Q2 KDV hariç taban: 4.38 / 6.17 / 2.94; vergilerle ≈
5.57 / 7.85 / 3.74).

**SAATLİK MAHSUPLAŞMA:** 2 Nisan 2026 RG değişikliğiyle aylık mahsup kalktı;
**1 Mayıs 2026'dan itibaren üretim-tüketim saat bazında netleşir.** Saat içi
fazla üretim şebekeye verilir ve dağıtım bedeli/vergiler düşülmüş fiyattan
(≈ perakende ×0.70; sektör örneği mesken ~3.5 TL/kWh) satın alınır.
Sonuçlar:
- Öz tüketim her saatte satıştan kârlıdır → cihazı üretim saatine kaydırmak
  **birebir parasal kazançtır** (ürünün varlık sebebi bu maddeyle güçlendi).
- Üç zamanlı aboneye özel nüans: gündüz **satış** fiyatı gece **alış**
  fiyatından yüksek olabilir → optimizer o kullanıcıya "gündüz sat, esnek yükü
  geceye al" diyebilir. Bu bir hata değil, mevzuatın doğru ekonomisidir
  (test: `test_three_zone_device_never_enters_peak`).
- Mesken çatı GES mahsuplaşma sınırı **10 kW** — uygulama aşan kullanıcıyı
  proaktif uyarır.

## 5. Optimizasyon

Deterministik ve açıklanabilir (LLM plana karar VERMEZ; planı anlatır):
saatlik net yük; ithalat alış, ihracat **o saatin** satış fiyatından; cihazlar
maliyeti minimize eden saate (eşitlikte üretim fazlası en bol saat); batarya
fazlayla şarj, pahalı saatte deşarj (%90 verim); tasarruf referansı alışkanlık
saati (ev 19:00, işyeri mesai başı).

## 6. Karşı-olgusal rapor (dürüstlük çerçevesi)

"Uygulasaydın X TL kazanırdın" **simülasyondur**: uygulanan öneriler
"gerçekleşen", uygulanmayanlar "kaçırılan fırsat"; ekranda "simülasyon"
ibaresi her zaman görünür.

## 7. Çevresel ve sosyal etki

- **Emisyon faktörü:** ETKB "Türkiye Ulusal Elektrik Şebekesi Emisyon Faktörü
  Bilgi Formu" (rev. 03.2024): üretim EF ≈ 0.434–0.439 tCO2e/MWh →
  uygulamada **0.44 kg CO₂e/kWh**.
- **Somutlaştırma eşdeğerleri:** olgun ağaç ~22 kg CO₂/yıl (EPA/One Tree
  Planted ortalaması); ortalama binek araç ~0.17 kg CO₂/km. Uygulama CO₂'yi
  "X km araba yolu" ve "Y ağacın aylık emilimi" olarak gösterir.
- **SDG hizası:** SDG 7 (Erişilebilir ve Temiz Enerji) — öz tüketimi artırıp
  faturayı düşürür; SDG 13 (İklim Eylemi) — fosil ağırlıklı şebeke ithalatını
  güneş saatlerine kaydırır. Puant kırpma, şebekenin en kirli/pahalı
  saatlerdeki yükünü azaltarak **toplumsal fayda** üretir (tek hanenin ötesinde
  sistem etkisi — sunum anlatısında kullanın).

## Kaynaklar

- EPDK tarife tabloları: https://www.epdk.gov.tr/Detay/Icerik/3-1327/elektrik-faturalarina-esas-tarife-tablolari
- Piagrid 2026 fiyat derlemesi: https://www.piagrid.com/indirimli-elektrik/elektrik-fiyati
- AA — "Lisanssız elektrik üretiminde saatlik mahsuplaşma dönemi başladı": https://www.aa.com.tr/tr/enerjiterminali/genel/lisanssiz-elektrik-uretiminde-saatlik-mahsuplasma-donemi-basladi/56064
- Lisanssız Elektrik Üretim Yönetmeliği (konsolide): https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=31502&MevzuatTur=7&MevzuatTertip=5
- MarsEnerji 2026 mahsuplaşma rehberi: https://marsenerji.com/lisanssiz-ges-mahsuplasma/
- ETKB Emisyon Faktörü Bilgi Formu: https://enerji.gov.tr/Media/Dizin/EVCED/tr/%C3%87evreVe%C4%B0klim/%C4%B0klimDe%C4%9Fi%C5%9Fikli%C4%9Fi/EmisyonFaktorleri/TEUVETN_Emisyon_Fakt%C3%B6rleri_Bilgi_Formu.pdf
- Akıllı Tarife — üç zamanlı saatler/fiyatlar: https://akillitarife.com/enerji/rehber/tarife/elektrik/ucuz-saatler
