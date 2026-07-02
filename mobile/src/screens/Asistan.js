// Asistan: Gemini agent ile serbest Türkçe sohbet.
// İtiraz/tercih bildirilince agent hafızaya yazar ve planı yeniden kurar;
// şeffaflık için çağrılan tool zinciri mesajın altında gösterilir.

import React, { useRef, useState } from 'react';
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable,
  ScrollView, Text, TextInput, View,
} from 'react-native';
import { api } from '../api';
import { EkranBasligi } from '../components/Marka';
import { bosluk, font, renk, yazi } from '../theme';

const ORNEKLER = [
  'Yarın için plan yapar mısın?',
  'Çamaşırı ne zaman atayım?',
  'Salı öğlen evde olmayacağım',
  'Bu ay ne kadar tasarruf ettim?',
];

export default function Asistan({ kullaniciId }) {
  const [mesajlar, setMesajlar] = useState([
    {
      rol: 'asistan',
      metin:
        'Merhaba! Ben Voltaic. Panelinin üretimini, tüketimini ve tarifeni izliyorum. ' +
        'Bana "yarın için plan yap" diyebilir ya da alışkanlıklarını söyleyebilirsin — hatırlarım.',
    },
  ]);
  const [girdi, setGirdi] = useState('');
  const [bekliyor, setBekliyor] = useState(false);
  const kaydirici = useRef(null);

  const gonder = async (metin) => {
    const mesaj = (metin ?? girdi).trim();
    if (!mesaj || bekliyor) return;
    setGirdi('');
    setMesajlar((m) => [...m, { rol: 'kullanici', metin: mesaj }]);
    setBekliyor(true);
    try {
      const yanit = await api.asistan(kullaniciId, mesaj);
      setMesajlar((m) => [
        ...m,
        {
          rol: 'asistan',
          metin: yanit.yanit,
          araclar: yanit.arac_cagrilari,
          mod: yanit.agent_modu,
        },
      ]);
    } catch {
      setMesajlar((m) => [
        ...m,
        { rol: 'asistan', metin: 'Sunucuya ulaşamadım — Ayarlar\'dan API adresini kontrol eder misin?' },
      ]);
    } finally {
      setBekliyor(false);
      setTimeout(() => kaydirici.current?.scrollToEnd({ animated: true }), 100);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: renk.sayfa }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        ref={kaydirici}
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: bosluk.m, paddingTop: 56 }}
      >
        <EkranBasligi baslik="Asistan" />

        {mesajlar.map((m, i) => (
          <View
            key={i}
            style={{
              alignSelf: m.rol === 'kullanici' ? 'flex-end' : 'flex-start',
              backgroundColor: m.rol === 'kullanici' ? renk.amber : renk.yuzey,
              borderRadius: 18,
              borderBottomRightRadius: m.rol === 'kullanici' ? 5 : 18,
              borderBottomLeftRadius: m.rol === 'kullanici' ? 18 : 5,
              borderWidth: m.rol === 'kullanici' ? 0 : 1,
              borderColor: renk.kenar,
              padding: 13,
              marginBottom: bosluk.s,
              maxWidth: '86%',
            }}
          >
            <Text style={{
              color: m.rol === 'kullanici' ? renk.amberUstuMurekkep : renk.murekkep,
              fontSize: 14.5, lineHeight: 21,
              fontFamily: m.rol === 'kullanici' ? font.orta : font.govde,
            }}>
              {m.metin}
            </Text>
            {m.araclar?.length > 0 && (
              <View style={{
                marginTop: 8, paddingTop: 8,
                borderTopWidth: 1, borderTopColor: renk.cizgi,
              }}>
                <Text style={[yazi.kucuk, { fontSize: 10.5, lineHeight: 15 }]}>
                  {m.araclar.join('  →  ')}
                  {m.mod === 'fallback' ? '   ·   kural modu' : ''}
                </Text>
              </View>
            )}
          </View>
        ))}
        {bekliyor && <ActivityIndicator style={{ marginVertical: bosluk.s }} color={renk.amber} />}

        {mesajlar.length <= 1 && (
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginTop: bosluk.s }}>
            {ORNEKLER.map((ornek) => (
              <Pressable
                key={ornek}
                onPress={() => gonder(ornek)}
                style={{
                  borderWidth: 1, borderColor: renk.kenar, borderRadius: 18,
                  paddingVertical: 9, paddingHorizontal: 13,
                  marginRight: bosluk.s, marginBottom: bosluk.s, backgroundColor: renk.yuzey,
                }}
              >
                <Text style={[yazi.kucuk, { color: renk.murekkepIkincil }]}>{ornek}</Text>
              </Pressable>
            ))}
          </View>
        )}
      </ScrollView>

      <View style={{ flexDirection: 'row', padding: bosluk.m, gap: bosluk.s }}>
        <TextInput
          value={girdi}
          onChangeText={setGirdi}
          placeholder="Sorunu yaz veya alışkanlığını söyle…"
          placeholderTextColor={renk.soluk}
          style={{
            flex: 1, backgroundColor: renk.girdi, borderWidth: 1, borderColor: renk.kenar,
            borderRadius: 24, paddingHorizontal: 16, paddingVertical: 11,
            fontSize: 14.5, color: renk.murekkep, fontFamily: font.govde,
          }}
          onSubmitEditing={() => gonder()}
        />
        <Pressable
          onPress={() => gonder()}
          style={{
            backgroundColor: renk.amber, borderRadius: 24, width: 46, height: 46,
            alignItems: 'center', justifyContent: 'center',
          }}
        >
          <Text style={{ color: renk.amberUstuMurekkep, fontSize: 17, fontFamily: font.kalin }}>↑</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}
