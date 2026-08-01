// Wattra — root component.
// Auth flow: no token → Login/Register, token + no profile → Onboarding, otherwise → main app.
// Screens are not shown until the brand fonts (Space Grotesk + Inter) load.

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
import { AuthProvider, useAuth } from './src/AuthContext';
import { SettingsIcon, ChartIcon, BoltIcon, ChatIcon } from './src/components/Icons';
import Assistant from './src/screens/Assistant';
import Login from './src/screens/Login';
import Onboarding from './src/screens/Onboarding';
import Register from './src/screens/Register';
import Report from './src/screens/Report';
import Settings from './src/screens/Settings';
import Today from './src/screens/Today';
import { font, colors } from './src/theme';

const Tab = createBottomTabNavigator();
// Tab route names are the Turkish labels shown to the user.
const ICONS = { Bugün: BoltIcon, Asistan: ChatIcon, Rapor: ChartIcon, Ayarlar: SettingsIcon };

const NavTheme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: colors.page,
    card: colors.surface,
    border: 'transparent',
    primary: colors.amber,
    text: colors.ink,
  },
};

async function scheduleNotifications(userId) {
  // Web does not support scheduled system notifications; alerts are already
  // shown as cards on the Today screen.
  if (Platform.OS === 'web') return;
  try {
    const { status } = await Notifications.requestPermissionsAsync();
    if (status !== 'granted') return;
    const { notifications } = await api.notifications(userId);
    await Notifications.cancelAllScheduledNotificationsAsync();
    // Tomorrow's opportunities are reminded at 20:00 (proactive agent behaviour)
    for (const alert of notifications.slice(0, 2)) {
      const now = new Date();
      const target = new Date(now);
      target.setHours(20, 0, 0, 0);
      if (target <= now) target.setDate(target.getDate() + 1);
      await Notifications.scheduleNotificationAsync({
        content: { title: alert.title, body: alert.text },
        trigger: target,
      });
    }
  } catch {
    // notification permission/network error must not block the app
  }
}

function AppContent() {
  const { user, loading, isAuthenticated } = useAuth();
  const [authScreen, setAuthScreen] = useState('login'); // 'login' | 'register'
  const [onboardingDone, setOnboardingDone] = useState(false);

  // Check if user has completed onboarding (has a real profile stored)
  useEffect(() => {
    if (!isAuthenticated) { setOnboardingDone(false); return; }
    AsyncStorage.getItem('onboarding_done_' + user.id).then((val) => {
      setOnboardingDone(val === 'true');
    });
  }, [isAuthenticated, user?.id]);

  useEffect(() => {
    if (user && onboardingDone) scheduleNotifications(user.id);
  }, [user, onboardingDone]);

  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.page }}>
        <ActivityIndicator color={colors.amber} size="large" />
      </View>
    );
  }

  // Not authenticated → show Login or Register
  if (!isAuthenticated) {
    return (
      <>
        <StatusBar style="light" />
        {authScreen === 'login' ? (
          <Login onSwitchToRegister={() => setAuthScreen('register')} />
        ) : (
          <Register onSwitchToLogin={() => setAuthScreen('login')} />
        )}
      </>
    );
  }

  // Authenticated but hasn't completed onboarding
  if (!onboardingDone) {
    return (
      <>
        <StatusBar style="light" />
        <Onboarding
          userId={user.id}
          onDone={async () => {
            await AsyncStorage.setItem('onboarding_done_' + user.id, 'true');
            setOnboardingDone(true);
          }}
        />
      </>
    );
  }

  // Authenticated + onboarding complete → main app
  return (
    <NavigationContainer theme={NavTheme}>
      <StatusBar style="light" />
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarActiveTintColor: colors.amber,
          tabBarInactiveTintColor: colors.faint,
          tabBarStyle: {
            backgroundColor: colors.surface,
            borderTopWidth: 1,
            borderTopColor: colors.border,
            height: 62,
            paddingTop: 6,
          },
          tabBarLabelStyle: { fontFamily: font.medium, fontSize: 11, paddingBottom: 6 },
          tabBarIcon: ({ color }) => {
            const Icon = ICONS[route.name];
            return <Icon size={22} color={color} />;
          },
        })}
      >
        <Tab.Screen name="Bugün">
          {() => <Today userId={user.id} />}
        </Tab.Screen>
        <Tab.Screen name="Asistan">
          {() => <Assistant userId={user.id} />}
        </Tab.Screen>
        <Tab.Screen name="Rapor">
          {() => <Report userId={user.id} />}
        </Tab.Screen>
        <Tab.Screen name="Ayarlar">
          {() => <Settings userId={user.id} />}
        </Tab.Screen>
      </Tab.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  const [fontsReady] = useFonts({
    Inter_400Regular, Inter_500Medium, Inter_600SemiBold,
    SpaceGrotesk_500Medium, SpaceGrotesk_700Bold,
  });

  if (!fontsReady) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.page }}>
        <ActivityIndicator color={colors.amber} size="large" />
      </View>
    );
  }

  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
