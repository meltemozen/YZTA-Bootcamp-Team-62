// Assistant: conversational access to the user's energy plan.

import React, { useRef, useState } from 'react';
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable,
  ScrollView, Text, TextInput, View,
} from 'react-native';
import { api } from '../api';
import { ScreenHeader } from '../components/Brand';
import { TOUCH } from '../components/States';
import { spacing, font, colors, text } from '../theme';

const EXAMPLES = [
  'Yarın en verimli saatler hangileri?',
  'Çamaşır makinesini ne zaman çalıştırayım?',
  'Yarın öğlen evde olmayacağım',
  'Planımı kısaca açıklar mısın?',
];

export default function Assistant({ userId }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text:
        'Merhaba! Enerji planınla ilgili sorularını yanıtlayabilirim. ' +
        'Cihazların için uygun saatleri sorabilir veya günlük planını değiştirecek bir tercihini yazabilirsin.',
    },
  ]);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(false);
  const scroller = useRef(null);

  const send = async (t) => {
    const message = (t ?? input).trim();
    if (!message || pending) return;
    setInput('');
    setMessages((m) => [...m, { role: 'user', text: message }]);
    setPending(true);
    try {
      const resp = await api.assistant(userId, message);
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: resp.reply,
        },
      ]);
    } catch (err) {
      // Keep the question on the message so one tap can retry it — retyping
      // after a dropped connection is the most annoying way to lose work.
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          failed: message,
          text: err?.status === 503
            ? 'Asistan şu anda yanıt veremiyor. Biraz sonra tekrar deneyebilirsin.'
            : 'Cevabı alamadım. Bağlantını kontrol edip tekrar deneyebilirsin.',
        },
      ]);
    } finally {
      setPending(false);
      setTimeout(() => scroller.current?.scrollToEnd({ animated: true }), 100);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.page }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        ref={scroller}
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: spacing.m, paddingTop: 56 }}
      >
        <ScreenHeader title="Asistan" />

        {messages.map((m, i) => (
          <View
            key={i}
            style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              backgroundColor: m.role === 'user' ? colors.amber : colors.surface,
              borderRadius: 18,
              borderBottomRightRadius: m.role === 'user' ? 5 : 18,
              borderBottomLeftRadius: m.role === 'user' ? 18 : 5,
              borderWidth: m.role === 'user' ? 0 : 1,
              borderColor: colors.border,
              padding: 13,
              marginBottom: spacing.s,
              maxWidth: '86%',
            }}
          >
            <Text style={{
              color: m.role === 'user' ? colors.amberInk : colors.ink,
              fontSize: 14.5, lineHeight: 21,
              fontFamily: m.role === 'user' ? font.medium : font.body,
            }}>
              {m.text}
            </Text>
            {m.failed && (
              <Pressable
                onPress={() => send(m.failed)}
                disabled={pending}
                accessibilityRole="button"
                accessibilityLabel="Mesajı tekrar gönder"
                style={{
                  marginTop: 10, minHeight: TOUCH, borderRadius: 12, borderWidth: 1,
                  borderColor: colors.amber, alignItems: 'center', justifyContent: 'center',
                  opacity: pending ? 0.5 : 1,
                }}
              >
                <Text style={{ color: colors.amber, fontFamily: font.semibold, fontSize: 13.5 }}>
                  Tekrar dene
                </Text>
              </Pressable>
            )}
          </View>
        ))}
        {pending && <ActivityIndicator style={{ marginVertical: spacing.s }} color={colors.amber} />}

        {messages.length <= 1 && (
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginTop: spacing.s }}>
            {EXAMPLES.map((example) => (
              <Pressable
                key={example}
                onPress={() => send(example)}
                accessibilityRole="button"
                accessibilityLabel={`Örnek soru: ${example}`}
                style={{
                  borderWidth: 1, borderColor: colors.border, borderRadius: 18,
                  paddingVertical: 12, paddingHorizontal: 14,
                  marginRight: spacing.s, marginBottom: spacing.s, backgroundColor: colors.surface,
                }}
              >
                <Text style={[text.small, { color: colors.inkSecondary }]}>{example}</Text>
              </Pressable>
            ))}
          </View>
        )}
      </ScrollView>

      <View style={{ flexDirection: 'row', padding: spacing.m, gap: spacing.s }}>
        <TextInput
          value={input}
          onChangeText={setInput}
          placeholder="Enerji planınla ilgili bir şey sor…"
          placeholderTextColor={colors.faint}
          style={{
            flex: 1, backgroundColor: colors.input, borderWidth: 1, borderColor: colors.border,
            borderRadius: 24, paddingHorizontal: 16, paddingVertical: 11,
            fontSize: 14.5, color: colors.ink, fontFamily: font.body,
          }}
          onSubmitEditing={() => send()}
        />
        <Pressable
          onPress={() => send()}
          disabled={pending || !input.trim()}
          accessibilityRole="button"
          accessibilityLabel="Gönder"
          accessibilityState={{ disabled: pending || !input.trim() }}
          style={{
            backgroundColor: colors.amber, borderRadius: 24, width: 46, height: 46,
            alignItems: 'center', justifyContent: 'center',
            opacity: pending || !input.trim() ? 0.4 : 1,
          }}
        >
          {pending
            ? <ActivityIndicator color={colors.amberInk} size="small" />
            : <Text style={{ color: colors.amberInk, fontSize: 17, fontFamily: font.semibold }}>↑</Text>}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}
