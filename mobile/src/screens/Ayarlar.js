// Ayarlar: API adresi (Expo Go testinde bilgisayarın LAN IP'si) + profil özeti
// + hesabı sıfırlama.

import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { api, apiUrl } from '../api';
import { onayla, uyar } from '../bildir';
import { EkranBasligi, LogoIsareti } from '../components/Marka';
import { birincilButon, birincilButonMetin, bosluk, font, kart, renk, yazi } from '../theme';

export default function Ayarlar({ kullaniciId, sifirla }) {
  const [url, setUrl] = useState('');
  const [profil, setProfil] = useState(null);

  useEffect(() => {
    apiUrl().then(setUrl);
    api.profil(kullaniciId).then(setProfil).catch(() => {});
  }, [kullaniciId]);

  const urlKaydet = async () => {
    await AsyncStorage.setItem('apiUrl', url.trim().replace(/\/$/, ''));
    uyar('Kaydedildi', 'API adresi güncellendi.');
  };

  const hesapSifirla = () =>
    onayla('Hesabı sıfırla', 'Kurulum baştan yapılacak. Emin misin?', 'Sıfırla',
      async () => {
        await AsyncStorage.removeItem('kullaniciId');
        sifirla();
      });

  return (
    <ScrollView style={{ flex: 1, backgroundColor: renk.sayfa }}
                contentContainerStyle={{ padding: bosluk.m, paddingTop: 56 }}>
      <EkranBasligi baslik="Ayarlar" />

      {profil && (
        <View style={kart}>
          <Text style={yazi.etiket}>Sistemin</Text>
          <Text style={[yazi.govde, { marginTop: bosluk.s, lineHeight: 23 }]}>
            {profil.kullanici_tipi === 'ev' ? 'Ev' : 'İşyeri'} · {profil.il} ·{' '}
            <Text style={{ color: renk.amber, fontFamily: font.orta }}>
              {profil.panel_kw} kW panel
            </Text>
            {profil.batarya_kwh > 0 ? ` · ${profil.batarya_kwh} kWh batarya` : ' · batarya yok'}
            {'\n'}Fatura: {profil.fatura_kwh_aylik} kWh/ay ·{' '}
            {profil.tarife_tipi === 'uc_zamanli' ? 'üç zamanlı' : 'tek zamanlı'} tarife
            {'\n'}Cihazlar: {profil.cihazlar.map((c) => c.ad).join(', ') || '—'}
          </Text>
        </View>
      )}

      <View style={kart}>
        <Text style={yazi.etiket}>Sunucu adresi</Text>
        <Text style={[yazi.kucuk, { marginVertical: bosluk.s }]}>
          Expo Go ile test ederken bilgisayarının yerel ağ IP'sini yaz
          (örn. http://192.168.1.34:8000). Canlı sürümde dokunma.
        </Text>
        <TextInput
          value={url}
          onChangeText={setUrl}
          autoCapitalize="none"
          style={{
            borderWidth: 1, borderColor: renk.kenar, borderRadius: 12,
            padding: 12, fontSize: 13.5, backgroundColor: renk.girdi,
            color: renk.murekkep, fontFamily: font.govde,
          }}
        />
        <Pressable onPress={urlKaydet}
                   style={[birincilButon, { paddingVertical: 12, marginTop: bosluk.s }]}>
          <Text style={[birincilButonMetin, { fontSize: 14 }]}>Kaydet</Text>
        </Pressable>
      </View>

      <Pressable onPress={hesapSifirla} style={[kart, { alignItems: 'center' }]}>
        <Text style={{ color: renk.kritik, fontFamily: font.kalin, fontSize: 14 }}>
          Hesabı sıfırla
        </Text>
      </Pressable>

      <View style={{ alignItems: 'center', marginTop: bosluk.m, gap: 8 }}>
        <LogoIsareti boyut={28} />
        <Text style={[yazi.kucuk, { textAlign: 'center', lineHeight: 17 }]}>
          Voltaic v0.1 · YZTA Bootcamp Takım 62{'\n'}
          Tarife: EPDK · Hava: Open-Meteo · Işınım: PVGIS
        </Text>
      </View>
    </ScrollView>
  );
}
