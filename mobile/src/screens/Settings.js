// Settings: profile summary + Profile link + logout.

import React, { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { api } from '../api';
import { useAuth } from '../AuthContext';
import { confirmAction, alertUser } from '../notify';
import { ScreenHeader, LogoMark } from '../components/Brand';
import Profile from './Profile';
import {
  DeviceEditor, LocationEditor, SystemEditor, TariffEditor,
} from '../components/ProfileEditors';
import { ErrorState, LoadingState, TOUCH } from '../components/States';
import {
  dangerButton, dangerButtonText, spacing, font, card, colors, text,
} from '../theme';

export default function Settings({ userId, onProfileChange }) {
  const { user, logout } = useAuth();
  const [profile, setProfile] = useState(null);
  const [profileError, setProfileError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [catalog, setCatalog] = useState([]);
  const [showProfile, setShowProfile] = useState(false);

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

  useEffect(() => { loadProfile(); }, [loadProfile]);
  useEffect(() => {
    api.deviceCatalog().then((d) => setCatalog(d.devices)).catch(() => setCatalog([]));
  }, []);

  const saveProfile = async (next, options = {}) => {
    try {
      await api.updateProfile(userId, next);
      setProfile(next);
      onProfileChange?.();   // make Bugün/Rapor rebuild with the new profile
      if (!options.silent) {
        alertUser('Kaydedildi', 'Planın yeni bilgilerle güncellendi.');
      }
      return true;
    } catch (e) {
      if (!options.silent) {
        alertUser('Kaydedilemedi', 'Bağlantı kurulamadı. Değişiklik kaydedilmedi.');
      }
      return false;
    }
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

      {loading && !profile && <LoadingState label="Profilin yükleniyor…" />}

      {profileError && !profile && (
        <ErrorState
          title="Profil okunamadı"
          message="Sistem bilgilerin şu anda alınamadı."
          hint="Bağlantını kontrol edip tekrar dene."
          onRetry={loadProfile}
        />
      )}

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

      {profile && (
        <>
          <LocationEditor profile={profile} onSave={saveProfile} />
          <SystemEditor profile={profile} onSave={saveProfile} />
          <TariffEditor profile={profile} onSave={saveProfile} />
          <DeviceEditor profile={profile} catalog={catalog} onSave={saveProfile} />
        </>
      )}

      {/* Logout */}
      <Pressable onPress={handleLogout} style={[dangerButton, { marginBottom: spacing.m }]}>
        <Text style={dangerButtonText}>Çıkış Yap</Text>
      </Pressable>

      <View style={{ alignItems: 'center', marginTop: spacing.s, gap: 8 }}>
        <LogoMark size={28} />
        <Text style={[text.small, { textAlign: 'center', lineHeight: 17 }]}>
          Wattra
        </Text >
      </View >
    </ScrollView >
  );
}
