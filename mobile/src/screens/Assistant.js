// Assistant: free Turkish chat with the Gemini agent.
// When an objection/preference is stated the agent writes it to memory and
// re-plans; for transparency the chain of called tools is shown under the message.

import React, { useRef, useState } from 'react';
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable,
  ScrollView, Text, TextInput, View,
} from 'react-native';
import { api } from '../api';
import { ScreenHeader } from '../components/Brand';
import { spacing, font, colors, text } from '../theme';

const EXAMPLES = [
  'Yarın için plan yapar mısın?',
  'Çamaşırı ne zaman atayım?',
  'Salı öğlen evde olmayacağım',
  'Bu ay ne kadar tasarruf ettim?',
];

export default function Assistant({ userId }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text:
        'Merhaba! Ben Voltaic. Panelinin üretimini, tüketimini ve tarifeni izliyorum. ' +
        'Bana "yarın için plan yap" diyebilir ya da alışkanlıklarını söyleyebilirsin — hatırlarım.',
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
          tools: resp.tool_calls,
          mode: resp.agent_mode,
        },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: 'assistant', text: 'Sunucuya ulaşamadım — Ayarlar\'dan API adresini kontrol eder misin?' },
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
            {m.tools?.length > 0 && (
              <View style={{
                marginTop: 8, paddingTop: 8,
                borderTopWidth: 1, borderTopColor: colors.line,
              }}>
                <Text style={[text.small, { fontSize: 10.5, lineHeight: 15 }]}>
                  {m.tools.join('  →  ')}
                  {m.mode === 'fallback' ? '   ·   kural modu' : ''}
                </Text>
              </View>
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
                style={{
                  borderWidth: 1, borderColor: colors.border, borderRadius: 18,
                  paddingVertical: 9, paddingHorizontal: 13,
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
          placeholder="Sorunu yaz veya alışkanlığını söyle…"
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
          style={{
            backgroundColor: colors.amber, borderRadius: 24, width: 46, height: 46,
            alignItems: 'center', justifyContent: 'center',
          }}
        >
          <Text style={{ color: colors.amberInk, fontSize: 17, fontFamily: font.semibold }}>↑</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}
