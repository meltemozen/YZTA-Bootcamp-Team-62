// Settings: API address (the computer's LAN IP during Expo Go testing) +
// profile summary + Profile link + logout.

import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { api, apiUrl } from '../api';
import { useAuth } from '../AuthContext';
import { confirmAction, alertUser } from '../notify';
import { ScreenHeader, LogoMark } from '../components/Brand';
import Profile from './Profile';
import {
  primaryButton, primaryButtonText, dangerButton, dangerButtonText,
  secondaryButton, secondaryButtonText, spacing, font, card, colors, text,
} from '../theme';

export default function Settings({ userId }) {
  const { user, logout } = useAuth();
  const [url, setUrl] = useState('');
  const [profile, setProfile] = useState(null);
  const [showProfile, setShowProfile] = useState(false);

  useEffect(() => {
    apiUrl().then(setUrl);
    api.profile(userId).then(setProfile).catch(() => {});
  }, [userId]);

  const saveUrl = async () => {
    await AsyncStorage.setItem('apiUrl', url.trim().replace(/\/$/, ''));
    alertUser('Kaydedildi', 'API adresi güncellendi.');
  };

  const handleLogout = () =>
    confirmAction('Çıkış Yap', 'Hesabından çıkış yapılacak. Emin misin?', 'Çıkış Yap',
      async () => {
        await logout();
      });

  if (showProfile) {
    return <Profile onBack={() => setShowProfile(false)} />;
  }

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.page }}
                contentContainerStyle={{ padding: spacing.m, paddingTop: 56 }}>
      <ScreenHeader title="Ayarlar" />

      {/* User card */}
      {user && (
        <Pressable onPress={() => setShowProfile(true)} style={card}>
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <View style={{ flex: 1 }}>
              <Text style={[text.subtitle, { marginBottom: 2 }]}>
                {user.name || 'Kullanıcı'}
              </Text>
              <Text style={text.small}>{user.email}</Text>
            </View>
            <View style={{
              width: 44, height: 44, borderRadius: 22,
              backgroundColor: colors.amberSoft, alignItems: 'center', justifyContent: 'center',
            }}>
              <Text style={{ fontSize: 20, color: colors.amber, fontFamily: font.title }}>
                {(user.name || 'U')[0].toUpperCase()}
              </Text>
            </View>
          </View>
          <Text style={[text.small, { marginTop: spacing.s, color: colors.amber }]}>
            Profili Görüntüle →
          </Text>
        </Pressable>
      )}

      {/* System summary */}
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

      {/* API address */}
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

      {/* Logout */}
      <Pressable onPress={handleLogout} style={[dangerButton, { marginBottom: spacing.m }]}>
        <Text style={dangerButtonText}>Çıkış Yap</Text>
      </Pressable>

      <View style={{ alignItems: 'center', marginTop: spacing.s, gap: 8 }}>
        <LogoMark size={28} />
        <Text style={[text.small, { textAlign: 'center', lineHeight: 17 }]}>
          Wattra v0.2 · YZTA Bootcamp Takım 62{'\n'}
          Tarife: EPDK · Hava: Open-Meteo · Işınım: PVGIS
        </Text>
      </View>
    </ScrollView>
  );
}
