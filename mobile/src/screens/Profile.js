// Profile — kullanıcı profili ekranı.
// Kullanıcı adı, e-posta, sistem bilgileri, şifre değiştirme ve çıkış.

import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator, Pressable, ScrollView, Text, TextInput, View,
} from 'react-native';
import { useAuth } from '../AuthContext';
import { api } from '../api';
import { alertUser } from '../notify';
import { ScreenHeader } from '../components/Brand';
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

  // Password change
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNew, setConfirmNew] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);
  const [errorPassword, setErrorPassword] = useState('');

  useEffect(() => {
    if (!user) return;
    api.authMe().then((me) => {
      setProfile(me.profile);
      setName(me.name || '');
      setEmail(me.email || '');
    }).catch(() => {});
  }, [user]);

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
      const msg = err.message || '';
      if (msg.includes('409')) {
        setErrorName('Bu e-posta adresi zaten başka bir hesap tarafından kullanılıyor.');
      } else if (msg.includes('422')) {
        setErrorName('Geçersiz formatta e-posta adresi girdiniz.');
      } else {
        setErrorName(`Hata: ${msg}`);
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
      const msg = err.message || '';
      if (msg.includes('401')) {
        setErrorPassword('Mevcut şifre yanlış.');
      } else {
        setErrorPassword(`Hata oluştu: ${msg}`);
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

      {/* User info card */}
      <View style={card}>
        <Text style={text.label}>KULLANICI BİLGİLERİ</Text>

        {/* Profile Info */}
        <View style={{ marginTop: spacing.m }}>
          <Text style={[text.small, { marginBottom: 4 }]}>Ad Soyad</Text>
          {editMode ? (
            <View style={{ gap: 12 }}>
              {errorName ? (
                <Text style={{ color: colors.critical, fontSize: 13 }}>{errorName}</Text>
              ) : null}
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
            {profile.user_type === 'home' ? '🏠 Ev' : '🏢 İşyeri'} · {profile.city}{'\n'}
            <Text style={{ color: colors.amber, fontFamily: font.medium }}>
              ⚡ {profile.panel_kw} kW panel
            </Text>
            {profile.battery_kwh > 0 ? ` · 🔋 ${profile.battery_kwh} kWh batarya` : ' · batarya yok'}
            {'\n'}📄 Fatura: {profile.monthly_bill_kwh} kWh/ay ·{' '}
            {profile.tariff_type === 'three_zone' ? 'üç zamanlı' : 'tek zamanlı'} tarife
            {'\n'}🔌 Cihazlar: {profile.devices?.map((d) => d.name).join(', ') || '—'}
          </Text>
          <Text style={[text.small, { marginTop: spacing.s }]}>
            Sistem bilgilerini değiştirmek için Ayarlar ekranından hesabı sıfırla ve
            kurulumu yeniden yap.
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
            {errorPassword ? (
              <View style={{ backgroundColor: 'rgba(242,109,109,0.12)', padding: spacing.m, borderRadius: 12, marginBottom: spacing.m, borderWidth: 1, borderColor: 'rgba(242,109,109,0.25)' }}>
                <Text style={[text.body, { color: colors.critical, fontSize: 14 }]}>{errorPassword}</Text>
              </View>
            ) : null}
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
