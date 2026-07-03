// Settings: API address (the computer's LAN IP during Expo Go testing) +
// profile summary + reset account.

import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { api, apiUrl } from '../api';
import { confirmAction, alertUser } from '../notify';
import { ScreenHeader, LogoMark } from '../components/Brand';
import { primaryButton, primaryButtonText, spacing, font, card, colors, text } from '../theme';

export default function Settings({ userId, onReset }) {
  const [url, setUrl] = useState('');
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    apiUrl().then(setUrl);
    api.profile(userId).then(setProfile).catch(() => {});
  }, [userId]);

  const saveUrl = async () => {
    await AsyncStorage.setItem('apiUrl', url.trim().replace(/\/$/, ''));
    alertUser('Kaydedildi', 'API adresi güncellendi.');
  };

  const resetAccount = () =>
    confirmAction('Hesabı sıfırla', 'Kurulum baştan yapılacak. Emin misin?', 'Sıfırla',
      async () => {
        await AsyncStorage.removeItem('userId');
        onReset();
      });

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.page }}
                contentContainerStyle={{ padding: spacing.m, paddingTop: 56 }}>
      <ScreenHeader title="Ayarlar" />

      {profile && (
        <View style={card}>
          <Text style={text.label}>Sistemin</Text>
          <Text style={[text.body, { marginTop: spacing.s, lineHeight: 23 }]}>
            {profile.user_type === 'home' ? 'Ev' : 'İşyeri'} · {profile.city} ·{' '}
            <Text style={{ color: colors.amber, fontFamily: font.medium }}>
              {profile.panel_kw} kW panel
            </Text>
            {profile.battery_kwh > 0 ? ` · ${profile.battery_kwh} kWh batarya` : ' · batarya yok'}
            {'\n'}Fatura: {profile.monthly_bill_kwh} kWh/ay ·{' '}
            {profile.tariff_type === 'three_zone' ? 'üç zamanlı' : 'tek zamanlı'} tarife
            {'\n'}Cihazlar: {profile.devices.map((d) => d.name).join(', ') || '—'}
          </Text>
        </View>
      )}

      <View style={card}>
        <Text style={text.label}>Sunucu adresi</Text>
        <Text style={[text.small, { marginVertical: spacing.s }]}>
          Expo Go ile test ederken bilgisayarının yerel ağ IP'sini yaz
          (örn. http://192.168.1.34:8000). Canlı sürümde dokunma.
        </Text>
        <TextInput
          value={url}
          onChangeText={setUrl}
          autoCapitalize="none"
          style={{
            borderWidth: 1, borderColor: colors.border, borderRadius: 12,
            padding: 12, fontSize: 13.5, backgroundColor: colors.input,
            color: colors.ink, fontFamily: font.body,
          }}
        />
        <Pressable onPress={saveUrl}
                   style={[primaryButton, { paddingVertical: 12, marginTop: spacing.s }]}>
          <Text style={[primaryButtonText, { fontSize: 14 }]}>Kaydet</Text>
        </Pressable>
      </View>

      <Pressable onPress={resetAccount} style={[card, { alignItems: 'center' }]}>
        <Text style={{ color: colors.critical, fontFamily: font.semibold, fontSize: 14 }}>
          Hesabı sıfırla
        </Text>
      </Pressable>

      <View style={{ alignItems: 'center', marginTop: spacing.m, gap: 8 }}>
        <LogoMark size={28} />
        <Text style={[text.small, { textAlign: 'center', lineHeight: 17 }]}>
          Voltaic v0.1 · YZTA Bootcamp Takım 62{'\n'}
          Tarife: EPDK · Hava: Open-Meteo · Işınım: PVGIS
        </Text>
      </View>
    </ScrollView>
  );
}
