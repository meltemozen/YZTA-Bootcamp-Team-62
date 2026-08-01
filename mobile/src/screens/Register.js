// Register — ad, e-posta, şifre ile kayıt ekranı.
// Kayıt sonrası Onboarding akışına yönlendirilir (profil bilgileri orada alınır).

import React, { useState } from 'react';
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable,
  ScrollView, Text, TextInput, View,
} from 'react-native';
import { useAuth } from '../AuthContext';
import { alertUser } from '../notify';
import { LogoMark, Wordmark } from '../components/Brand';
import {
  primaryButton, primaryButtonText, inputField, linkText,
  spacing, font, card, colors, text,
} from '../theme';

// Default profile for initial registration — user will fill real values in Onboarding
const DEFAULT_PROFILE = {
  user_type: 'home',
  city: 'İzmir',
  lat: 38.42,
  lon: 27.14,
  panel_kw: 5,
  battery_kwh: 0,
  battery_power_kw: 0,
  monthly_bill_kwh: 300,
  tariff_type: 'single',
  devices: [],
};

export default function Register({ onSwitchToLogin }) {
  const { register } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleRegister = async () => {
    setError('');
    if (!name.trim()) {
      setError('Lütfen adını gir.');
      return;
    }
    if (!email.trim()) {
      setError('Lütfen e-posta adresini gir.');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setError('Lütfen geçerli bir e-posta adresi gir.');
      return;
    }
    if (password.length < 6) {
      setError('Şifre en az 6 karakter olmalı.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Şifreler aynı değil, tekrar kontrol et.');
      return;
    }

    setLoading(true);
    try {
      await register(email.trim(), password, name.trim(), DEFAULT_PROFILE);
    } catch (err) {
      const msg = err.message || '';
      if (msg.includes('409')) {
        setError('Bu e-posta adresi zaten kullanılıyor. Giriş yapmayı dene.');
      } else if (msg.includes('422')) {
        setError('Geçersiz formatta bilgi girdiniz. E-posta adresinizi kontrol edin.');
      } else {
        setError(`Kayıt başarısız. Bir hata oluştu: ${msg}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.page }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        contentContainerStyle={{
          flexGrow: 1, justifyContent: 'center',
          padding: spacing.l, paddingBottom: 40,
        }}
        keyboardShouldPersistTaps="handled"
      >
        {/* Brand hero */}
        <View style={{ alignItems: 'center', marginBottom: spacing.l }}>
          <LogoMark size={48} />
          <View style={{ height: 10 }} />
          <Wordmark size={28} />
        </View>

        {/* Registration card */}
        <View style={[card, { paddingVertical: spacing.l }]}>
          <Text style={[text.title, { marginBottom: spacing.l, textAlign: 'center' }]}>
            Hesap Oluştur
          </Text>

          {error ? (
            <View style={{ backgroundColor: 'rgba(242,109,109,0.12)', padding: spacing.m, borderRadius: 12, marginBottom: spacing.m, borderWidth: 1, borderColor: 'rgba(242,109,109,0.25)' }}>
              <Text style={[text.body, { color: colors.critical, fontSize: 14 }]}>{error}</Text>
            </View>
          ) : null}

          <Text style={[text.label, { marginBottom: spacing.xs }]}>AD SOYAD</Text>
          <TextInput
            value={name}
            onChangeText={setName}
            placeholder="Adın Soyadın"
            placeholderTextColor={colors.faint}
            autoComplete="name"
            style={[inputField, { marginBottom: spacing.m }]}
          />

          <Text style={[text.label, { marginBottom: spacing.xs }]}>E-POSTA</Text>
          <TextInput
            value={email}
            onChangeText={setEmail}
            placeholder="ornek@mail.com"
            placeholderTextColor={colors.faint}
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
            style={[inputField, { marginBottom: spacing.m }]}
          />

          <Text style={[text.label, { marginBottom: spacing.xs }]}>ŞİFRE</Text>
          <TextInput
            value={password}
            onChangeText={setPassword}
            placeholder="En az 6 karakter"
            placeholderTextColor={colors.faint}
            secureTextEntry
            autoComplete="new-password"
            style={[inputField, { marginBottom: spacing.m }]}
          />

          <Text style={[text.label, { marginBottom: spacing.xs }]}>ŞİFRE TEKRAR</Text>
          <TextInput
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            placeholder="Şifreni tekrar gir"
            placeholderTextColor={colors.faint}
            secureTextEntry
            style={[inputField, { marginBottom: spacing.l }]}
          />

          <Pressable
            disabled={loading}
            onPress={handleRegister}
            style={[primaryButton, { opacity: loading ? 0.7 : 1 }]}
          >
            {loading ? (
              <ActivityIndicator color={colors.amberInk} />
            ) : (
              <Text style={primaryButtonText}>Kayıt Ol</Text>
            )}
          </Pressable>
        </View>

        {/* Switch to Login */}
        <View style={{ alignItems: 'center', marginTop: spacing.m }}>
          <Text style={text.body}>Zaten hesabın var mı?</Text>
          <Pressable onPress={onSwitchToLogin} style={{ padding: spacing.s }}>
            <Text style={linkText}>Giriş Yap</Text>
          </Pressable>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
