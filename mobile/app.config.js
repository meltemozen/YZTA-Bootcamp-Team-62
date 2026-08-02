const apiUrl = process.env.EXPO_PUBLIC_API_URL || '';
const buildNumber = process.env.IOS_BUILD_NUMBER || '1';
const versionCode = Number(process.env.ANDROID_VERSION_CODE || '1');
const easProjectId = process.env.EAS_PROJECT_ID || '31d763b5-5d2b-437a-b41c-0e4ea0f4a939';

const extra = { apiUrl };
if (easProjectId) {
  extra.eas = { projectId: easProjectId };
}

module.exports = {
  expo: {
    name: process.env.EXPO_PUBLIC_APP_NAME || 'Wattra',
    slug: 'wattra',
    version: process.env.EXPO_PUBLIC_APP_VERSION || '0.1.0',
    orientation: 'portrait',
    userInterfaceStyle: 'dark',
    backgroundColor: '#0b0f1a',
    icon: './assets/icon.png',
    splash: {
      backgroundColor: '#0b0f1a',
      image: './assets/splash-icon.png',
      resizeMode: 'contain',
    },
    android: {
      package: 'com.wattra.energy',
      versionCode,
      permissions: [
        'ACCESS_COARSE_LOCATION',
        'ACCESS_FINE_LOCATION',
        'POST_NOTIFICATIONS',
      ],
      adaptiveIcon: {
        backgroundColor: '#0b0f1a',
        foregroundImage: './assets/adaptive-icon.png',
      },
    },
    ios: {
      bundleIdentifier: 'com.wattra.energy',
      buildNumber,
      supportsTablet: false,
      infoPlist: {
        ITSAppUsesNonExemptEncryption: false,
        NSLocationWhenInUseUsageDescription:
          'Wattra konumunu yalnızca yerel hava ve güneş üretim tahminini hesaplamak için kullanır.',
        NSUserNotificationUsageDescription:
          'Wattra uygun güneş saatleri ve plan hatırlatmaları için bildirim göndermek ister.',
      },
    },
    web: {
      bundler: 'metro',
      output: 'single',
      name: 'Wattra — Çatı-GES Enerji Asistanı',
    },
    plugins: [
      'expo-asset',
      'expo-font',
      'expo-status-bar',
      [
        'expo-location',
        {
          locationWhenInUsePermission:
            'Wattra konumunu yalnızca yerel hava ve güneş üretim tahminini hesaplamak için kullanır.',
        },
      ],
    ],
    extra: {
      ...extra,
    },
  },
};
