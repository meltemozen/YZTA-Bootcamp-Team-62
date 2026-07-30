// Settings: API address (the computer's LAN IP during Expo Go testing) +
// profile summary + reset account.

import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { api, apiUrl } from '../api';
import { confirmAction, alertUser } from '../notify';
import { ScreenHeader, LogoMark } from '../components/Brand';
import { DeviceEditor, TariffEditor } from '../components/ProfileEditors';
import { ErrorState, LoadingState, TOUCH } from '../components/States';
import { primaryButton, primaryButtonText, spacing, font, card, colors, text } from '../theme';

export default function Settings({ userId, onReset, onProfileChange }) {
  const [url, setUrl] = useState('');
  const [profile, setProfile] = useState(null);
  const [profileError, setProfileError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [catalog, setCatalog] = useState([]);

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setProfileError(null);
    try {
      setProfile(await api.profile(userId));
    } catch (e) {
      setProfileError(e.message);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { apiUrl().then(setUrl); }, []);
  useEffect(() => { loadProfile(); }, [loadProfile]);
  useEffect(() => {
    api.deviceCatalog().then((d) => setCatalog(d.devices)).catch(() => setCatalog([]));
  }, []);

  const saveProfile = async (next) => {
    try {
      await api.updateProfile(userId, next);
      setProfile(next);
      onProfileChange?.();   // make Bugün/Rapor rebuild with the new profile
      alertUser('Kaydedildi', 'Planın yeni bilgilerle güncellendi.');
    } catch (e) {
      alertUser('Kaydedilemedi', `Sunucuya ulaşılamadı, değişiklik kaydedilmedi.\n\n${e.message}`);
    }
  };

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

      {loading && !profile && <LoadingState label="Profilin yükleniyor…" />}

      {profileError && !profile && (
        <ErrorState
          title="Profil okunamadı"
          message="Sistem bilgilerin sunucudan alınamadı."
          hint={`Aşağıdaki sunucu adresi doğru mu kontrol et. (${profileError})`}
          onRetry={loadProfile}
        />
      )}

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

      {profile && (
        <>
          <TariffEditor profile={profile} onSave={saveProfile} />
          <DeviceEditor profile={profile} catalog={catalog} onSave={saveProfile} />
        </>
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
                   accessibilityRole="button"
                   accessibilityLabel="Sunucu adresini kaydet"
                   style={[primaryButton, {
                     paddingVertical: 12, marginTop: spacing.s, minHeight: TOUCH,
                     justifyContent: 'center',
                   }]}>
          <Text style={[primaryButtonText, { fontSize: 14 }]}>Kaydet</Text>
        </Pressable>
      </View>

      <Pressable onPress={resetAccount}
                 accessibilityRole="button"
                 accessibilityLabel="Hesabı sıfırla ve kurulumu baştan yap"
                 style={[card, { alignItems: 'center', justifyContent: 'center', minHeight: TOUCH }]}>
        <Text style={{ color: colors.critical, fontFamily: font.semibold, fontSize: 14 }}>
          Hesabı sıfırla
        </Text>
      </Pressable>

      <View style={{ alignItems: 'center', marginTop: spacing.m, gap: 8 }}>
        <LogoMark size={28} />
        <Text style={[text.small, { textAlign: 'center', lineHeight: 17 }]}>
          Wattra v0.1 · YZTA Bootcamp Takım 62{'\n'}
          Hava tahmini: Open-Meteo (canlı) · Işınım geçmişi: PVGIS
        </Text>
        {/* Honesty: the tariff is NOT a live EPDK feed — it is a table baked
            into the app, so say the date and invite the user to compare. */}
        <Text style={[text.small, { textAlign: 'center', lineHeight: 17 }]}>
          Tarife fiyatları EPDK'nın 4 Nisan 2026 tablosundan alınıp uygulamaya
          gömülüdür; canlı bağlantı yoktur. Faturandaki birim fiyat farklıysa
          tasarruf tahminleri de o oranda değişir.
        </Text>
      </View>
    </ScrollView>
  );
}
