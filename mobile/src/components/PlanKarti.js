// Tek plan kalemi kartı: ikon rozeti, saat, tasarruf aralığı, gerekçe ve
// "Uyguladım" anahtarı (karşı-olgusal raporun ham verisi buradan gelir).

import React, { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { api, aralikTL, GEREKCE_METNI } from '../api';
import { BataryaIkon, PrizIkon, SimsekIkon } from './Ikonlar';
import { bosluk, font, kart, renk, yazi } from '../theme';

const TUR_IKON = { cihaz: PrizIkon, batarya_sarj: BataryaIkon, batarya_desarj: SimsekIkon };

export default function PlanKarti({ kalem, kullaniciId, tarih }) {
  const [uygulandi, setUygulandi] = useState(false);
  const [kaydediliyor, setKaydediliyor] = useState(false);

  const isaretle = async () => {
    const yeni = !uygulandi;
    setUygulandi(yeni);
    setKaydediliyor(true);
    try {
      await api.geribildirim({
        kullanici_id: kullaniciId,
        tarih,
        kalem_ad: kalem.ad,
        uygulandi: yeni,
      });
    } catch {
      setUygulandi(!yeni); // kaydedilemedi, geri al
    } finally {
      setKaydediliyor(false);
    }
  };

  const saat = `${String(kalem.baslangic_saat).padStart(2, '0')}:00–${String(
    kalem.bitis_saat
  ).padStart(2, '0')}:00`;
  const baslik =
    kalem.tur === 'batarya_sarj'
      ? 'Bataryayı güneşten doldur'
      : kalem.tur === 'batarya_desarj'
      ? 'Bataryayı kullan'
      : `${kalem.ad} çalıştır`;
  const Ikon = TUR_IKON[kalem.tur] || PrizIkon;

  return (
    <View style={kart}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <View style={{
          width: 42, height: 42, borderRadius: 21, backgroundColor: renk.amberYumusak,
          alignItems: 'center', justifyContent: 'center',
        }}>
          <Ikon boyut={21} renk={renk.amber} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={yazi.altBaslik}>{baslik}</Text>
          <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 8, marginTop: 3 }}>
            <Text style={{ fontFamily: font.rakam, fontSize: 15, color: renk.amber }}>
              {saat}
            </Text>
            {kalem.tasarruf_tl_max > 0 && (
              <Text style={{ fontFamily: font.orta, fontSize: 13, color: renk.murekkepIkincil }}>
                {aralikTL(kalem.tasarruf_tl_min, kalem.tasarruf_tl_max)}
              </Text>
            )}
          </View>
          <Text style={[yazi.kucuk, { marginTop: 3 }]}>
            {GEREKCE_METNI[kalem.gerekce_kodu] || ''}
          </Text>
        </View>
        {kalem.tur !== 'batarya_sarj' && (
          <Pressable
            onPress={isaretle}
            disabled={kaydediliyor}
            style={{
              paddingVertical: 7, paddingHorizontal: 13, borderRadius: 18,
              borderWidth: 1,
              borderColor: uygulandi ? renk.iyi : renk.kenar,
              backgroundColor: uygulandi ? renk.iyiZemin : 'transparent',
            }}
          >
            <Text style={{
              fontSize: 12, fontFamily: font.kalin,
              color: uygulandi ? renk.iyiMetin : renk.murekkepIkincil,
            }}>
              {uygulandi ? '✓ Uygulandı' : 'Uyguladım'}
            </Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}
