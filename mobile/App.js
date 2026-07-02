// Voltaic — kök bileşen.
// Akış: kayıtlı kullanıcı yoksa Onboarding, varsa 4 sekmeli ana uygulama.
// Marka fontları (Space Grotesk + Inter) yüklenmeden ekran gösterilmez.

import AsyncStorage from '@react-native-async-storage/async-storage';
import { DarkTheme, NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import {
  Inter_400Regular, Inter_500Medium, Inter_600SemiBold,
} from '@expo-google-fonts/inter';
import {
  SpaceGrotesk_500Medium, SpaceGrotesk_700Bold,
} from '@expo-google-fonts/space-grotesk';
import { useFonts } from 'expo-font';
import * as Notifications from 'expo-notifications';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Platform, View } from 'react-native';
import { api } from './src/api';
import { AyarIkon, GrafikIkon, SimsekIkon, SohbetIkon } from './src/components/Ikonlar';
import Asistan from './src/screens/Asistan';
import Ayarlar from './src/screens/Ayarlar';
import Bugun from './src/screens/Bugun';
import Onboarding from './src/screens/Onboarding';
import Rapor from './src/screens/Rapor';
import { font, renk } from './src/theme';

const Sekme = createBottomTabNavigator();
const IKONLAR = { Bugün: SimsekIkon, Asistan: SohbetIkon, Rapor: GrafikIkon, Ayarlar: AyarIkon };

const NavTema = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: renk.sayfa,
    card: renk.yuzey,
    border: 'transparent',
    primary: renk.amber,
    text: renk.murekkep,
  },
};

async function bildirimleriKur(kullaniciId) {
  // Web'de sistem bildirimi zamanlaması desteklenmez; uyarılar zaten
  // Bugün ekranında kart olarak gösteriliyor.
  if (Platform.OS === 'web') return;
  try {
    const { status } = await Notifications.requestPermissionsAsync();
    if (status !== 'granted') return;
    const { bildirimler } = await api.bildirimler(kullaniciId);
    await Notifications.cancelAllScheduledNotificationsAsync();
    // Yarının fırsatları akşam 20:00'de hatırlatılır (proaktif agent davranışı)
    for (const uyari of bildirimler.slice(0, 2)) {
      const simdi = new Date();
      const hedef = new Date(simdi);
      hedef.setHours(20, 0, 0, 0);
      if (hedef <= simdi) hedef.setDate(hedef.getDate() + 1);
      await Notifications.scheduleNotificationAsync({
        content: { title: uyari.baslik, body: uyari.metin },
        trigger: hedef,
      });
    }
  } catch {
    // bildirim izni/ağ hatası uygulamayı engellemez
  }
}

export default function App() {
  const [fontlarHazir] = useFonts({
    Inter_400Regular, Inter_500Medium, Inter_600SemiBold,
    SpaceGrotesk_500Medium, SpaceGrotesk_700Bold,
  });
  const [kullaniciId, setKullaniciId] = useState(null);
  const [hazir, setHazir] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem('kullaniciId').then((deger) => {
      if (deger) setKullaniciId(parseInt(deger, 10));
      setHazir(true);
    });
  }, []);

  useEffect(() => {
    if (kullaniciId) bildirimleriKur(kullaniciId);
  }, [kullaniciId]);

  if (!hazir || !fontlarHazir) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: renk.sayfa }}>
        <ActivityIndicator color={renk.amber} size="large" />
      </View>
    );
  }

  if (!kullaniciId) {
    return (
      <>
        <StatusBar style="light" />
        <Onboarding tamamlandi={setKullaniciId} />
      </>
    );
  }

  return (
    <NavigationContainer theme={NavTema}>
      <StatusBar style="light" />
      <Sekme.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarActiveTintColor: renk.amber,
          tabBarInactiveTintColor: renk.soluk,
          tabBarStyle: {
            backgroundColor: renk.yuzey,
            borderTopWidth: 1,
            borderTopColor: renk.kenar,
            height: 62,
            paddingTop: 6,
          },
          tabBarLabelStyle: { fontFamily: font.orta, fontSize: 11, paddingBottom: 6 },
          tabBarIcon: ({ color }) => {
            const Ikon = IKONLAR[route.name];
            return <Ikon boyut={22} renk={color} />;
          },
        })}
      >
        <Sekme.Screen name="Bugün">
          {() => <Bugun kullaniciId={kullaniciId} />}
        </Sekme.Screen>
        <Sekme.Screen name="Asistan">
          {() => <Asistan kullaniciId={kullaniciId} />}
        </Sekme.Screen>
        <Sekme.Screen name="Rapor">
          {() => <Rapor kullaniciId={kullaniciId} />}
        </Sekme.Screen>
        <Sekme.Screen name="Ayarlar">
          {() => <Ayarlar kullaniciId={kullaniciId} sifirla={() => setKullaniciId(null)} />}
        </Sekme.Screen>
      </Sekme.Navigator>
    </NavigationContainer>
  );
}
