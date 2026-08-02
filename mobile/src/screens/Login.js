// Login — e-posta + şifre ile giriş ekranı.
// Wattra brand hero + glassmorphism card tasarımı.

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

export default function Login({ onSwitchToRegister }) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async () => {
    setError('');
    if (!email.trim() || !password) {
      setError('E-posta ve şifre alanlarını doldur.');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setError('Geçerli bir e-posta adresi gir.');
      return;
    }
    setLoading(true);
    try {
      await login(email.trim(), password);
    } catch (err) {
      if (err.status === 401) {
        setError('E-posta veya şifre hatalı.');
      } else if (err.status === 422) {
        setError('Geçersiz e-posta formatı girdiniz.');
      } else {
        setError('Bağlantı kurulamadı. Lütfen biraz sonra tekrar dene.');
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
        <View style={{ alignItems: 'center', marginBottom: spacing.xl }}>
          <LogoMark size={56} />
          <View style={{ height: 12 }} />
          <Wordmark size={32} />
          <Text style={[text.body, { marginTop: 6, textAlign: 'center' }]}>
            Çatındaki güneş, akıllıca yönetilsin
          </Text>
        </View>

        {/* Login card */}
        <View style={[card, { paddingVertical: spacing.l }]}>
          <Text style={[text.title, { marginBottom: spacing.l, textAlign: 'center' }]}>
            Giriş Yap
          </Text>

          <InlineNotice tone="error" message={error} />

          <Text style={[text.label, { marginBottom: spacing.xs }]}>E-POSTA</Text>
          <TextInput
            value={email}
            onChangeText={(value) => { setEmail(value); setError(''); }}
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
            onChangeText={(value) => { setPassword(value); setError(''); }}
            placeholder="••••••••"
            placeholderTextColor={colors.faint}
            secureTextEntry
            autoComplete="password"
            style={[inputField, { marginBottom: spacing.l }]}
          />

          <Pressable
            disabled={loading}
            onPress={handleLogin}
            style={[primaryButton, { opacity: loading ? 0.7 : 1 }]}
          >
            {loading ? (
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.s }}>
                <ActivityIndicator color={colors.amberInk} />
                <Text style={primaryButtonText}>Giriş yapılıyor</Text>
              </View>
            ) : (
              <Text style={primaryButtonText}>Giriş Yap</Text>
            )}
          </Pressable>
        </View>

        {/* Switch to Register */}
        <View style={{ alignItems: 'center', marginTop: spacing.m }}>
          <Text style={text.body}>Hesabın yok mu?</Text>
          <Pressable onPress={onSwitchToRegister} style={{ padding: spacing.s }}>
            <Text style={linkText}>Kayıt Ol</Text>
          </Pressable>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
