# Sprint 1 — Retrospective

**Tarih:** 5 Temmuz 2026

## İyi gidenler (Keep)

- Model–agent kontratının ilk hafta kilitlenmesi iki ekibi paralel ilerletti —
  en büyük risk (iki ekip iki ayrı proje yapar) hiç gerçekleşmedi.
- Tek noktadan enerji sabitleri (`config.py`) + mevzuat kaynaklarının belgelenmesi
  (METHOD.md), fiyat/kural güncellemelerini tek dosyaya indirdi.
- Anahtarsız fallback sayesinde ürün her ortamda (demo dahil) çalıştı.

## Sorunlar (Problems)

- **Board plandan kopyalanmıştı, gerçek işe uymuyordu.** Kartlar orijinal PDF
  görev tablosundan birebir alınmıştı; yapılan iş (Gemini function-calling,
  JSON şema kontratı, saatlik mahsuplaşma) kartlarda birebir görünmüyordu.
- **Kod tabanı tamamen Türkçe adlandırılmıştı;** ekip İngilizce ilerlemeye karar
  vermişti ama kod bu kararı yansıtmıyordu.
- Herkesin kendi branch'inde ayrı klasör yapısı kurması küçük entegrasyon
  sürtünmesi yarattı.

## Aksiyonlar (Try / Action items)

1. **Repo refactor'ü yapıldı (bu sprint kapanışında):** kod tabanı İngilizce'ye
   taşındı (dosya/metot/sınıf/alan adları, tool adları, API route'ları, JSON
   alanları); **mobil arayüz metinleri Türkçe kaldı**. 14 test yeşil kaldı, mobil
   dosyalar syntax + referans taramasıyla doğrulandı. → *Karar: "sıfırla" yerine
   "koru + düzenle"; ilerleme çöpe atılmadı.*
2. **Board gerçek işe göre yeniden yazıldı** (8 net Sprint 1 kartı, story point'li).
3. **Sprint 2–3 gerçek kalan işe göre planlandı** (baseline → LightGBM, değerlendirme,
   canlıya alma, teslim). Toplam ≈ 100 SP netleşti.
4. **Bundan sonra:** tek ortak klasör mimarisi üzerinden çalışılacak; kartlar
   yapılan işle senkron tutulacak; PR'lar küçük ve sık.

## Metrikler

- Planlanan/tamamlanan: **45 / 45 SP.**
- Test: 14/14 yeşil. Ağ gerektirmez (deterministik).
