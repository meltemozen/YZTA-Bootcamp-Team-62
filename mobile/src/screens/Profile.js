// Profile — kullanıcı profili ekranı.
// Kullanıcı adı, e-posta, sistem bilgileri, şifre değiştirme ve çıkış.

import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator, Pressable, ScrollView, Text, TextInput, View,
} from 'react-native';
import { useAuth } from '../AuthContext';
import { api } from '../api';
import { alertUser } from '../notify';
import { ScreenHeader } from '../components/Brand';
import { ErrorState, InlineNotice, LoadingState } from '../components/States';
import {
  primaryButton, primaryButtonText, secondaryButton, secondaryButtonText,
  dangerButton, dangerButtonText, inputField, card, spacing, font, colors, text,
} from '../theme';

export default function Profile({ onBack }) {
  const { user, logout, updateUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [saving, setSaving] = useState(false);
  const [errorName, setErrorName] = useState('');
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileError, setProfileError] = useState(false);

  // Password change
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNew, setConfirmNew] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);
  const [errorPassword, setErrorPassword] = useState('');

  const loadProfile = useCallback(async () => {
    if (!user) return;
    setProfileLoading(true);
    setProfileError(false);
    try {
      const me = await api.authMe();
      setProfile(me.profile);
      setName(me.name || '');
      setEmail(me.email || '');
    } catch {
      setProfileError(true);
    } finally {
      setProfileLoading(false);
    }
  }, [user]);

  useEffect(() => { loadProfile(); }, [loadProfile]);

  const handleSaveProfile = async () => {
    setErrorName('');
    if (!name.trim() || !email.trim()) {
      setErrorName('İsim ve e-posta boş olamaz.');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setErrorName('Lütfen geçerli bir e-posta adresi girin.');
      return;
    }
    setSaving(true);
    try {
      const resp = await api.authUpdateMe({ name: name.trim(), email: email.trim() });
      updateUser({ name: resp.name, email: resp.email });
      setEditMode(false);
      alertUser('Güncellendi', 'Bilgilerin başarıyla değiştirildi.');
    } catch (err) {
      if (err.status === 409) {
        setErrorName('Bu e-posta adresi zaten başka bir hesap tarafından kullanılıyor.');
      } else if (err.status === 422) {
        setErrorName('Geçersiz formatta e-posta adresi girdiniz.');
      } else {
        setErrorName('Bilgilerin kaydedilemedi. Bağlantını kontrol edip yeniden dene.');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    setErrorPassword('');
    if (newPassword.length < 6) {
      setErrorPassword('Yeni şifre en az 6 karakter olmalı.');
      return;
    }
    if (newPassword !== confirmNew) {
      setErrorPassword('Yeni şifreler aynı değil.');
      return;
    }
    setChangingPassword(true);
    try {
      await api.authChangePassword(currentPassword, newPassword);
      alertUser('Başarılı', 'Şifren değiştirildi.');
      setShowPasswordChange(false);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNew('');
    } catch (err) {
      if (err.status === 401) {
        setErrorPassword('Mevcut şifre yanlış.');
      } else {
        setErrorPassword('Şifre değiştirilemedi. Bağlantını kontrol edip yeniden dene.');
      }
    } finally {
      setChangingPassword(false);
    }
  };

  const handleLogout = () => {
    logout();
  };

  if (!user) return null;

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.page }}
      contentContainerStyle={{ padding: spacing.m, paddingTop: 56 }}
    >
      <ScreenHeader title="Profilim" />

      {profileLoading ? <LoadingState label="Profil yükleniyor…" /> : null}
      {profileError ? (
        <ErrorState
          title="Profil yüklenemedi"
          message="Profil bilgilerin şu anda alınamadı."
          onRetry={loadProfile}
        />
      ) : null}

      {/* User info card */}
      <View style={card}>
        <Text style={text.label}>KULLANICI BİLGİLERİ</Text>

        {/* Profile Info */}
        <View style={{ marginTop: spacing.m }}>
          <Text style={[text.small, { marginBottom: 4 }]}>Ad Soyad</Text>
          {editMode ? (
            <View style={{ gap: 12 }}>
              <InlineNotice tone="error" message={errorName} />
              <View>
                <TextInput value={name} onChangeText={setName} style={inputField} />
              </View>
              <View>
                <Text style={[text.small, { marginBottom: 4 }]}>E-posta</Text>
                <TextInput 
                  value={email} 
                  onChangeText={setEmail} 
                  style={inputField} 
                  keyboardType="email-address" 
                  autoCapitalize="none" 
                />
              </View>
              <View style={{ flexDirection: 'row', gap: 8, marginTop: 4 }}>
                <Pressable onPress={handleSaveProfile} disabled={saving} style={[primaryButton, { flex: 1, paddingVertical: 12 }]}>
                  {saving ? <ActivityIndicator color={colors.amberInk} size="small" /> : <Text style={primaryButtonText}>Kaydet</Text>}
                </Pressable>
                <Pressable onPress={() => { setEditMode(false); setName(user.name || ''); setEmail(user.email || ''); setErrorName(''); }} style={[secondaryButton, { flex: 1, paddingVertical: 12 }]}>
                  <Text style={secondaryButtonText}>İptal</Text>
                </Pressable>
              </View>
            </View>
          ) : (
            <View style={{ flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between' }}>
              <View>
                <Text style={[text.body, { color: colors.ink, fontSize: 16 }]}>{user.name || '—'}</Text>
                <Text style={[text.small, { marginTop: 16, marginBottom: 4 }]}>E-posta</Text>
                <Text style={[text.body, { color: colors.ink, fontSize: 15 }]}>{user.email || '—'}</Text>
              </View>
              <Pressable onPress={() => setEditMode(true)} style={{ padding: 6 }}>
                <Text style={{ color: colors.amber, fontFamily: font.medium, fontSize: 13 }}>Düzenle</Text>
              </Pressable>
            </View>
          )}
        </View>
      </View>

      {/* System info card */}
      {profile && (
        <View style={card}>
          <Text style={text.label}>SİSTEM BİLGİLERİ</Text>
          <Text style={[text.body, { marginTop: spacing.s, lineHeight: 23 }]}>
            {profile.user_type === 'home' ? 'Ev' : 'İşyeri'} · {profile.city}{'\n'}
            <Text style={{ color: colors.amber, fontFamily: font.medium }}>
              {profile.panel_kw} kW panel
            </Text>
            {profile.battery_kwh > 0 ? ` · ${profile.battery_kwh} kWh batarya` : ' · batarya yok'}
            {'\n'}Fatura: {profile.monthly_bill_kwh} kWh/ay ·{' '}
            {profile.tariff_type === 'three_zone' ? 'üç zamanlı' : 'tek zamanlı'} tarife
            {'\n'}Cihazlar: {profile.devices?.map((d) => d.name).join(', ') || '—'}
          </Text>
        </View>
      )}

      {/* Password change */}
      <View style={card}>
        <Pressable
          onPress={() => setShowPasswordChange(!showPasswordChange)}
          style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <Text style={text.label}>ŞİFRE DEĞİŞTİR</Text>
          <Text style={[text.body, { fontSize: 13 }]}>
            {showPasswordChange ? '▲' : '▼'}
          </Text>
        </Pressable>

        {showPasswordChange && (
          <View style={{ marginTop: spacing.m }}>
            <InlineNotice tone="error" message={errorPassword} />
            <Text style={[text.small, { marginBottom: 4 }]}>Mevcut Şifre</Text>
            <TextInput
              value={currentPassword}
              onChangeText={setCurrentPassword}
              secureTextEntry
              style={[inputField, { marginBottom: spacing.s }]}
            />
            <Text style={[text.small, { marginBottom: 4 }]}>Yeni Şifre</Text>
            <TextInput
              value={newPassword}
              onChangeText={setNewPassword}
              secureTextEntry
              placeholder="En az 6 karakter"
              placeholderTextColor={colors.faint}
              style={[inputField, { marginBottom: spacing.s }]}
            />
            <Text style={[text.small, { marginBottom: 4 }]}>Yeni Şifre (Tekrar)</Text>
            <TextInput
              value={confirmNew}
              onChangeText={setConfirmNew}
              secureTextEntry
              style={[inputField, { marginBottom: spacing.m }]}
            />
            <Pressable
              onPress={handleChangePassword}
              disabled={changingPassword}
              style={[secondaryButton, { opacity: changingPassword ? 0.6 : 1 }]}
            >
              {changingPassword ? (
                <ActivityIndicator color={colors.ink} size="small" />
              ) : (
                <Text style={secondaryButtonText}>Şifreyi Güncelle</Text>
              )}
            </Pressable>
          </View>
        )}
      </View>

      {/* Logout */}
      <Pressable onPress={handleLogout} style={[dangerButton, { marginBottom: spacing.xl }]}>
        <Text style={dangerButtonText}>Çıkış Yap</Text>
      </Pressable>
    </ScrollView>
  );
}
