"""hafiza_oku / hafiza_yaz tool'ları.

Agent'ın "öğrenen hafıza" yeteneği: kullanıcı tercihi ("salı öğlen evde
kimse yok") ve agent çıkarımları burada tutulur; her plan üretiminde
okunup Gemini bağlamına verilir.

MVP arka ucu SQLite'tır. YZ-3 için genişletme noktası: semantik arama
istenirse Chroma eklenip `tercihler_ara(sorgu)` fonksiyonu bu modüle
eklenir — tool imzaları değişmez.
"""

from .. import db


def hafiza_oku(kullanici_id: int) -> list[dict]:
    return db.tercihler(kullanici_id)


def hafiza_yaz(kullanici_id: int, metin: str, kaynak: str = "kullanici") -> dict:
    db.tercih_ekle(kullanici_id, metin, kaynak)
    return {"durum": "kaydedildi", "metin": metin}
