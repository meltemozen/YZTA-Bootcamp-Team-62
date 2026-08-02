// Register — ad, e-posta, şifre ile kayıt ekranı.
// Kayıt sonrası Onboarding akışına yönlendirilir (profil bilgileri orada alınır).

import React, { useState } from 'react';
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable,
  ScrollView, Text, TextInput, View,
} from 'react-native';
import { useAuth } from '../AuthContext';
import { LogoMark, Wordmark } from '../components/Brand';
import { InlineNotice } from '../components/States';
import {
  primaryButton, primaryButtonText, inputField, linkText,
  spacing, font, card, colors, text,
} from '../theme';

export default function Register({ onSwitchToLogin }) {
  const { register } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [touched, setTouched] = useState({});

  const fieldErrors = {
    name: name.trim() ? '' : 'Adını ve soyadını gir.',
    email: !email.trim()
      ? 'E-posta adresini gir.'
      : /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())
        ? '' : 'Geçerli bir e-posta adresi gir.',
    password: password.length >= 6 ? '' : 'Şifre en az 6 karakter olmalı.',
    confirmPassword: !confirmPassword
      ? 'Şifreni tekrar gir.'
      : password === confirmPassword ? '' : 'Şifreler aynı değil.',
  };

  const fieldMessage = (field) => touched[field] && fieldErrors[field] ? (
    <Text accessibilityRole="alert" style={[
      text.small, { color: colors.critical, marginTop: -spacing.s, marginBottom: spacing.m },
    ]}>
      {fieldErrors[field]}
    </Text>
  ) : null;

  const updateField = (setter) => (value) => {
    setter(value);
    if (error) setError('');
  };

  const handleRegister = async () => {
    setError('');
    setTouched({ name: true, email: true, password: true, confirmPassword: true });
    if (Object.values(fieldErrors).some(Boolean)) {
      setError('Devam etmek için işaretli alanları düzelt.');
      return;
    }

    setLoading(true);
    try {
      await register(email.trim(), password, name.trim());
    } catch (err) {
      if (err.status === 409) {
        setError('Bu e-posta adresi zaten kullanılıyor. Giriş yapmayı dene.');
      } else if (err.status === 422) {
        setError('Geçersiz formatta bilgi girdiniz. E-posta adresinizi kontrol edin.');
      } else {
        setError('Kayıt tamamlanamadı. Bağlantını kontrol edip yeniden dene.');
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

          <InlineNotice tone="error" message={error} />

          <Text style={[text.label, { marginBottom: spacing.xs }]}>AD SOYAD</Text>
          <TextInput
            value={name}
            onChangeText={updateField(setName)}
            onBlur={() => setTouched((current) => ({ ...current, name: true }))}
            placeholder="Adın Soyadın"
            placeholderTextColor={colors.faint}
            autoComplete="name"
            style={[inputField, { marginBottom: spacing.m }]}
          />
          {fieldMessage('name')}

          <Text style={[text.label, { marginBottom: spacing.xs }]}>E-POSTA</Text>
          <TextInput
            value={email}
            onChangeText={updateField(setEmail)}
            onBlur={() => setTouched((current) => ({ ...current, email: true }))}
            placeholder="ornek@mail.com"
            placeholderTextColor={colors.faint}
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
            style={[inputField, { marginBottom: spacing.m }]}
          />
          {fieldMessage('email')}

          <Text style={[text.label, { marginBottom: spacing.xs }]}>ŞİFRE</Text>
          <TextInput
            value={password}
            onChangeText={updateField(setPassword)}
            onBlur={() => setTouched((current) => ({ ...current, password: true }))}
            placeholder="En az 6 karakter"
            placeholderTextColor={colors.faint}
            secureTextEntry
            autoComplete="new-password"
            style={[inputField, { marginBottom: spacing.m }]}
          />
          {fieldMessage('password')}

          <Text style={[text.label, { marginBottom: spacing.xs }]}>ŞİFRE TEKRAR</Text>
          <TextInput
            value={confirmPassword}
            onChangeText={updateField(setConfirmPassword)}
            onBlur={() => setTouched((current) => ({ ...current, confirmPassword: true }))}
            placeholder="Şifreni tekrar gir"
            placeholderTextColor={colors.faint}
            secureTextEntry
            style={[inputField, { marginBottom: spacing.l }]}
          />
          {fieldMessage('confirmPassword')}

          <Pressable
            disabled={loading}
            onPress={handleRegister}
            style={[primaryButton, { opacity: loading ? 0.7 : 1 }]}
          >
            {loading ? (
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.s }}>
                <ActivityIndicator color={colors.amberInk} />
                <Text style={primaryButtonText}>Hesap oluşturuluyor</Text>
              </View>
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
