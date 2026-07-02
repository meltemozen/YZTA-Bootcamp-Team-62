// Ay sonu raporu: gerçekleşen tasarruf + kaçırılan fırsat (karşı-olgusal) + CO2.
// Rakamlar simülasyon temellidir ve ekranda bu dürüstçe belirtilir.

import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, Text, View } from 'react-native';
import { api, aralikTL } from '../api';
import { EkranBasligi } from '../components/Marka';
import { bosluk, font, kart, renk, yazi } from '../theme';

function Kutu({ etiket, deger, altMetin, rengi }) {
  return (
    <View style={[kart, { flex: 1, marginRight: bosluk.s }]}>
      <Text style={yazi.etiket}>{etiket}</Text>
      <Text style={{
        fontFamily: font.baslik, fontSize: 24, letterSpacing: -0.3,
        color: rengi || renk.murekkep, marginTop: 6,
      }}>
        {deger}
      </Text>
      {altMetin ? <Text style={[yazi.kucuk, { marginTop: 4 }]}>{altMetin}</Text> : null}
    </View>
  );
}

export default function Rapor({ kullaniciId }) {
  const [rapor, setRapor] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(true);

  const yukle = useCallback(async () => {
    setYukleniyor(true);
    try {
      setRapor(await api.rapor(kullaniciId));
    } catch {
      setRapor(null);
    } finally {
      setYukleniyor(false);
    }
  }, [kullaniciId]);

  useEffect(() => { yukle(); }, [yukle]);

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: renk.sayfa }}
      contentContainerStyle={{ padding: bosluk.m, paddingTop: 56 }}
      refreshControl={
        <RefreshControl refreshing={yukleniyor} onRefresh={yukle} tintColor={renk.amber} />
      }
    >
      <EkranBasligi baslik="Ay Sonu Raporu" />

      {yukleniyor && !rapor && <ActivityIndicator style={{ marginTop: 48 }} color={renk.amber} />}

      {rapor && (
        <>
          <View style={{ flexDirection: 'row' }}>
            <Kutu
              etiket="Gerçekleşen"
              deger={aralikTL(rapor.gerceklesen_tasarruf_tl_min, rapor.gerceklesen_tasarruf_tl_max)}
              altMetin={`${rapor.uygulanan_oneri}/${rapor.toplam_oneri} öneri uygulandı`}
              rengi={renk.iyiMetin}
            />
            <Kutu
              etiket="Kaçırılan fırsat"
              deger={`${rapor.kacirilan_tasarruf_tl.toFixed(0)} TL`}
              altMetin="uygulanmayan öneriler"
              rengi={renk.amber}
            />
          </View>
          <View style={{ flexDirection: 'row' }}>
            <Kutu
              etiket="Önlenen karbon"
              deger={`${rapor.co2_tasarruf_kg.toFixed(1)} kg`}
              altMetin={`≈ ${rapor.araba_km_esdegeri.toFixed(0)} km araba yolu`}
              rengi={renk.iyiMetin}
            />
            <Kutu
              etiket="Ağaç eşdeğeri"
              deger={`${rapor.agac_ay_esdegeri.toFixed(1)} ağaç`}
              altMetin="bir aylık emilim gücü"
              rengi={renk.iyiMetin}
            />
          </View>

          <View style={[kart, { borderLeftWidth: 3, borderLeftColor: renk.amber }]}>
            <Text style={yazi.altBaslik}>Voltaic'in yorumu · {rapor.ay}</Text>
            <Text style={[yazi.govde, { marginTop: bosluk.s }]}>{rapor.aciklama}</Text>
            <Text style={[yazi.kucuk, { marginTop: bosluk.s }]}>
              Çevresel etki, ETKB şebeke emisyon faktörüyle (0.44 kg CO₂e/kWh) hesaplanır.
              Güneşe kaydırdığın her kWh, şebekenin en yoğun saatlerindeki yükü de azaltır.
            </Text>
          </View>

          <Text style={[yazi.kucuk, { textAlign: 'center', marginTop: bosluk.s, lineHeight: 17 }]}>
            Tasarruf rakamları tarife + üretim tahminine dayalı simülasyondur;{'\n'}
            sayaç ölçümü değildir. Yöntem: docs/METHOD.md
          </Text>
        </>
      )}
    </ScrollView>
  );
}
