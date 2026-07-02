// Onboarding: 4 adımda kurulum → 5 dakikada ilk öneri.
// Kullanıcıdan yalnızca BİLDİĞİ şeyler istenir: ev mi işyeri mi, hangi il,
// panel gücü, aylık fatura ve evdeki esnek cihazlar. Saatlik tüketim verisi
// İSTENMEZ — backend fatura kalibrasyonuyla tahmin eder.

import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator, Pressable, ScrollView, Text, TextInput, View,
} from 'react-native';
import { api } from '../api';
import { uyar } from '../bildir';
import { LogoIsareti, SozMarkasi } from '../components/Marka';
import {
  birincilButon, birincilButonMetin, bosluk, font, kart, renk, yazi,
} from '../theme';

const ILLER = [
  { ad: 'İstanbul', enlem: 41.01, boylam: 28.98 },
  { ad: 'Ankara', enlem: 39.93, boylam: 32.86 },
  { ad: 'İzmir', enlem: 38.42, boylam: 27.14 },
  { ad: 'Antalya', enlem: 36.9, boylam: 30.7 },
  { ad: 'Bursa', enlem: 40.19, boylam: 29.06 },
  { ad: 'Adana', enlem: 37.0, boylam: 35.32 },
  { ad: 'Konya', enlem: 37.87, boylam: 32.48 },
  { ad: 'Gaziantep', enlem: 37.07, boylam: 37.38 },
  { ad: 'Kayseri', enlem: 38.72, boylam: 35.49 },
  { ad: 'Şanlıurfa', enlem: 37.16, boylam: 38.79 },
  { ad: 'Denizli', enlem: 37.78, boylam: 29.09 },
  { ad: 'Muğla', enlem: 37.22, boylam: 28.36 },
];

function Secenek({ etiket, secili, onPress, kucuk }) {
  return (
    <Pressable
      onPress={onPress}
      style={{
        paddingVertical: kucuk ? 9 : 14,
        paddingHorizontal: 15,
        borderRadius: 12,
        borderWidth: 1.5,
        borderColor: secili ? renk.amber : renk.kenar,
        backgroundColor: secili ? renk.amberYumusak : renk.girdi,
        marginBottom: bosluk.s,
        marginRight: bosluk.s,
      }}
    >
      <Text style={{
        fontFamily: secili ? font.kalin : font.govde,
        fontSize: 14,
        color: secili ? renk.amber : renk.murekkepIkincil,
      }}>
        {etiket}
      </Text>
    </Pressable>
  );
}

function SayiGirisi({ etiket, deger, setDeger, birim }) {
  return (
    <View style={{ marginBottom: bosluk.m }}>
      <Text style={[yazi.govde, { marginBottom: 6 }]}>{etiket}</Text>
      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
        <TextInput
          value={deger}
          onChangeText={setDeger}
          keyboardType="numeric"
          style={{
            borderWidth: 1, borderColor: renk.kenar, borderRadius: 12,
            padding: 13, fontSize: 17, width: 120,
            backgroundColor: renk.girdi, color: renk.murekkep,
            fontFamily: font.rakam,
          }}
        />
        <Text style={[yazi.govde, { marginLeft: bosluk.s }]}>{birim}</Text>
      </View>
    </View>
  );
}

export default function Onboarding({ tamamlandi }) {
  const [adim, setAdim] = useState(0);
  const [tip, setTip] = useState('ev');
  const [il, setIl] = useState(ILLER[2]);
  const [panelKw, setPanelKw] = useState('5');
  const [bataryaKwh, setBataryaKwh] = useState('0');
  const [fatura, setFatura] = useState('300');
  const [tarife, setTarife] = useState('tek_zamanli');
  const [katalog, setKatalog] = useState([]);
  const [secilenCihazlar, setSecilenCihazlar] = useState([]);
  const [gonderiliyor, setGonderiliyor] = useState(false);

  useEffect(() => {
    api.cihazReferans().then((d) => setKatalog(d.cihazlar)).catch(() => {});
  }, []);

  const cihazSecili = (ad) => secilenCihazlar.some((c) => c.ad === ad);
  const cihazDegistir = (cihaz) =>
    setSecilenCihazlar((mevcut) =>
      cihazSecili(cihaz.ad) ? mevcut.filter((c) => c.ad !== cihaz.ad) : [...mevcut, cihaz]
    );

  const bitir = async () => {
    setGonderiliyor(true);
    try {
      const batarya = parseFloat(bataryaKwh) || 0;
      const yanit = await api.kayit({
        kullanici_tipi: tip,
        il: il.ad,
        enlem: il.enlem,
        boylam: il.boylam,
        panel_kw: parseFloat(panelKw) || 5,
        batarya_kwh: batarya,
        batarya_guc_kw: batarya > 0 ? Math.min(batarya / 2, 5) : 0,
        fatura_kwh_aylik: parseFloat(fatura) || 300,
        tarife_tipi: tarife,
        cihazlar: secilenCihazlar,
      });
      await AsyncStorage.setItem('kullaniciId', String(yanit.kullanici_id));
      tamamlandi(yanit.kullanici_id);
    } catch (hata) {
      uyar(
        'Bağlantı sorunu',
        `Sunucuya ulaşılamadı. Ayarlar > API adresini kontrol edin.\n\n${hata.message}`
      );
    } finally {
      setGonderiliyor(false);
    }
  };

  const adimlar = [
    <View key="tip">
      <Text style={[yazi.baslik, { marginBottom: bosluk.m }]}>Panelin nerede kurulu?</Text>
      <View style={{ flexDirection: 'row' }}>
        <Secenek etiket="Evim" secili={tip === 'ev'} onPress={() => setTip('ev')} />
        <Secenek etiket="İşyerim" secili={tip === 'isyeri'} onPress={() => setTip('isyeri')} />
      </View>
      <Text style={[yazi.baslik, { marginVertical: bosluk.m }]}>Hangi ilde?</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
        {ILLER.map((sehir) => (
          <Secenek key={sehir.ad} kucuk etiket={sehir.ad}
                   secili={il.ad === sehir.ad} onPress={() => setIl(sehir)} />
        ))}
      </View>
    </View>,

    <View key="panel">
      <Text style={[yazi.baslik, { marginBottom: bosluk.m }]}>Güneş sistemin</Text>
      <SayiGirisi etiket="Panel gücü (faturanda veya sözleşmende yazar)"
                  deger={panelKw} setDeger={setPanelKw} birim="kW" />
      <SayiGirisi etiket="Batarya kapasitesi (yoksa 0 bırak)"
                  deger={bataryaKwh} setDeger={setBataryaKwh} birim="kWh" />
      <Text style={yazi.kucuk}>
        Bataryan olmasa da Voltaic cihazlarını güneş saatlerine planlayarak tasarruf sağlar.
      </Text>
    </View>,

    <View key="fatura">
      <Text style={[yazi.baslik, { marginBottom: bosluk.m }]}>Elektrik faturan</Text>
      <SayiGirisi etiket="Aylık tüketimin (faturada 'kWh' yazan satır)"
                  deger={fatura} setDeger={setFatura} birim="kWh / ay" />
      <Text style={[yazi.govde, { marginBottom: bosluk.s }]}>Tarifen hangisi?</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
        <Secenek etiket="Tek zamanlı (bilmiyorum)" secili={tarife === 'tek_zamanli'}
                 onPress={() => setTarife('tek_zamanli')} />
        <Secenek etiket="Üç zamanlı" secili={tarife === 'uc_zamanli'}
                 onPress={() => setTarife('uc_zamanli')} />
      </View>
      <Text style={yazi.kucuk}>
        Çoğu abonelik tek zamanlıdır. Üç zamanlıda gece ucuz, 17-22 arası pahalıdır —
        emin değilsen faturanda "T1/T2/T3" satırları olup olmadığına bak.
      </Text>
    </View>,

    <View key="cihaz">
      <Text style={[yazi.baslik, { marginBottom: bosluk.s }]}>Hangi cihazların var?</Text>
      <Text style={[yazi.govde, { marginBottom: bosluk.m }]}>
        Zamanını kaydırabileceğin cihazları seç — Voltaic bunları en ucuz saate planlayacak.
      </Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
        {katalog
          .filter((c) => tip === 'isyeri' || !c.ad.includes('işyeri'))
          .map((cihaz) => (
            <Secenek key={cihaz.ad} kucuk etiket={cihaz.ad}
                     secili={cihazSecili(cihaz.ad)} onPress={() => cihazDegistir(cihaz)} />
          ))}
      </View>
    </View>,
  ];

  return (
    <ScrollView style={{ flex: 1, backgroundColor: renk.sayfa }}
                contentContainerStyle={{ padding: bosluk.l, paddingTop: 64 }}>
      {/* Marka hero */}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 6 }}>
        <LogoIsareti boyut={40} />
        <View>
          <SozMarkasi boyut={26} />
          <Text style={[yazi.kucuk, { marginTop: 1 }]}>Çatındaki güneş, akıllıca yönetilsin</Text>
        </View>
      </View>

      {/* İlerleme çubuğu */}
      <View style={{
        height: 4, backgroundColor: renk.girdi, borderRadius: 2,
        marginTop: bosluk.m, marginBottom: bosluk.l, overflow: 'hidden',
      }}>
        <View style={{
          height: 4, borderRadius: 2, backgroundColor: renk.amber,
          width: `${((adim + 1) / adimlar.length) * 100}%`,
        }} />
      </View>

      <View style={[kart, { minHeight: 320 }]}>{adimlar[adim]}</View>

      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Pressable disabled={adim === 0} onPress={() => setAdim(adim - 1)}
                   style={{ padding: 14, opacity: adim === 0 ? 0.25 : 1 }}>
          <Text style={[yazi.govde, { fontFamily: font.orta }]}>← Geri</Text>
        </Pressable>
        <Pressable
          disabled={gonderiliyor}
          onPress={() => (adim < adimlar.length - 1 ? setAdim(adim + 1) : bitir())}
          style={[birincilButon, { minWidth: 150 }]}
        >
          {gonderiliyor ? (
            <ActivityIndicator color={renk.amberUstuMurekkep} />
          ) : (
            <Text style={birincilButonMetin}>
              {adim < adimlar.length - 1 ? 'Devam' : 'Başla'}
            </Text>
          )}
        </Pressable>
      </View>
    </ScrollView>
  );
}
