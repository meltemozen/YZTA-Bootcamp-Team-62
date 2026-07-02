"""Model–Agent KONTRATI.

Bu dosya iki ekibin (YZ + VB) buluşma noktasıdır ve KİLİTLİDİR.
Tool imzaları ve veri tipleri burada tanımlanır; değişiklik ancak iki
ekibin ortak kararı + docs/CONTRACT.md güncellemesiyle yapılır.

Tüm saatlik diziler 24 elemanlıdır ve yerel saat 00:00-23:00'ı temsil eder.
"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Kullanıcı ve hane profili
# --------------------------------------------------------------------------

class Cihaz(BaseModel):
    """Esnek yük: kullanıcının zamanını kaydırabileceği cihaz."""
    ad: str
    kwh: float = Field(gt=0, description="Bir çalıştırmanın toplam tüketimi (kWh)")
    sure_saat: int = Field(ge=1, le=12, description="Çalışma süresi (saat, yukarı yuvarlanmış)")
    en_erken: int = Field(default=0, ge=0, le=23)
    en_gec: int = Field(default=23, ge=0, le=23, description="En geç BİTİŞ saati")


class HaneProfili(BaseModel):
    kullanici_tipi: Literal["ev", "isyeri"] = "ev"
    il: str = "İzmir"
    enlem: float = 38.42
    boylam: float = 27.14
    panel_kw: float = Field(gt=0, description="Kurulu panel gücü (kWp)")
    batarya_kwh: float = Field(default=0, ge=0, description="Batarya kapasitesi, 0 = yok")
    batarya_guc_kw: float = Field(default=0, ge=0, description="Maks şarj/deşarj gücü")
    fatura_kwh_aylik: float = Field(gt=0, description="Son fatura aylık tüketimi — kalibrasyon girdisi")
    tarife_tipi: Literal["tek_zamanli", "uc_zamanli"] = "tek_zamanli"
    cihazlar: list[Cihaz] = []
    mesai_baslangic: int = Field(default=8, ge=0, le=23, description="İşyeri için")
    mesai_bitis: int = Field(default=19, ge=0, le=23)


# --------------------------------------------------------------------------
# Tool girdi/çıktıları (kontratın kendisi)
# --------------------------------------------------------------------------

class HavaDurumu(BaseModel):
    """hava_getir(konum, tarih) çıktısı — Open-Meteo canlı verisi."""
    tarih: date
    isinim_wm2: list[float] = Field(description="Saatlik global yatay ışınım (W/m²), 24 eleman")
    sicaklik_c: list[float] = Field(description="Saatlik sıcaklık (°C), 24 eleman")
    bulutluluk_yuzde: list[float] = Field(description="Saatlik bulutluluk (%), 24 eleman")


class UretimTahmini(BaseModel):
    """uretim_tahmin(hava, panel_kw) çıktısı."""
    tarih: date
    saatlik_kwh: list[float] = Field(description="24 eleman")
    toplam_kwh: float
    model_surumu: str = Field(description="'v0-fiziksel' | 'v1-lightgbm' — VB ekibi v1'i takar")


class TuketimTahmini(BaseModel):
    """tuketim_tahmin(hane_profili) çıktısı — baz yük, esnek cihazlar HARİÇ."""
    tarih: date
    saatlik_kwh: list[float]
    toplam_kwh: float
    model_surumu: str = "v0-profil"


class TarifeBilgisi(BaseModel):
    """tarife_getir(tarih, kullanici_tipi, tarife_tipi, aylik_kwh) çıktısı.

    Kontrat v1.1: SAATLİK mahsuplaşma (RG 02.04.2026) gereği satış fiyatı
    saat bazına indirildi; tek zamanlı kademeli tarife için aylik_kwh girdisi
    eklendi (marjinal kademe fiyatı seçimi).
    """
    tarih: date
    saatlik_fiyat: list[float] = Field(description="Alış fiyatı TL/kWh (vergiler dahil), 24 eleman")
    saatlik_satis_fiyat: list[float] = Field(
        description="Saatlik mahsupta o saatin satış fiyatı TL/kWh (≈ alış × 0.70), 24 eleman")
    mahsup_satis_fiyati: float = Field(description="Günlük ortalama satış fiyatı (geriye uyum/özet)")
    dilim_adi: list[str] = Field(description="Her saat için 'gunduz'|'puant'|'gece'|'tek'")


class PlanKalemi(BaseModel):
    tur: Literal["cihaz", "batarya_sarj", "batarya_desarj"]
    ad: str
    baslangic_saat: int
    bitis_saat: int
    tasarruf_tl_min: float = Field(description="Belirsizlik aralığı alt sınır")
    tasarruf_tl_max: float
    gerekce_kodu: str = Field(description="'gunes_bol'|'puant_kacinma'|'gece_ucuz'|'mahsup_avantaji'")


class GunlukPlan(BaseModel):
    """optimize(...) çıktısı — agent'ın kullanıcıya çevireceği ham plan."""
    tarih: date
    kalemler: list[PlanKalemi]
    toplam_tasarruf_tl_min: float
    toplam_tasarruf_tl_max: float
    co2_tasarruf_kg: float
    oz_tuketim_orani: float = Field(description="Üretimin evde tüketilen payı 0-1")
    ozet_veri: dict = Field(default_factory=dict, description="Grafik için: uretim/tuketim/fiyat dizileri")


class KullaniciTercihi(BaseModel):
    """hafiza_oku/hafiza_yaz birimi."""
    metin: str = Field(description="Örn: 'Salı günleri öğlen evde kimse yok'")
    kaynak: Literal["kullanici", "cikarim"] = "kullanici"
    tarih: Optional[str] = None


# --------------------------------------------------------------------------
# API sözleşmeleri (mobil ↔ backend)
# --------------------------------------------------------------------------

class KayitIstek(BaseModel):
    profil: HaneProfili


class KayitYanit(BaseModel):
    kullanici_id: int
    mesaj: str


class AsistanIstek(BaseModel):
    kullanici_id: int
    mesaj: str = Field(description="Serbest Türkçe: soru, itiraz veya tercih")


class AsistanYanit(BaseModel):
    yanit: str = Field(description="Agent'ın gerekçeli Türkçe cevabı")
    plan: Optional[GunlukPlan] = None
    agent_modu: Literal["gemini", "fallback"]
    arac_cagrilari: list[str] = Field(default_factory=list, description="Şeffaflık: hangi tool'lar çağrıldı")


class GeriBildirim(BaseModel):
    kullanici_id: int
    tarih: date
    kalem_ad: str
    uygulandi: bool


class AylikRapor(BaseModel):
    ay: str
    uygulanan_oneri: int
    toplam_oneri: int
    gerceklesen_tasarruf_tl_min: float
    gerceklesen_tasarruf_tl_max: float
    kacirilan_tasarruf_tl: float = Field(description="Karşı-olgusal: uygulanmayan önerilerin değeri")
    co2_tasarruf_kg: float
    # Çevresel/sosyal etki eşdeğerleri (SDG 7 & 13 anlatısı)
    araba_km_esdegeri: float = Field(default=0, description="Önlenen CO2'nin araç km karşılığı")
    agac_ay_esdegeri: float = Field(default=0, description="Kaç ağacın aylık emilimine denk")
    aciklama: str
