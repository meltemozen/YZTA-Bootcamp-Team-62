// Backend API client.
// BASE_URL priority: address saved on the Settings screen → app.json extra.
// When testing on a phone with Expo Go, use the computer's LOCAL NETWORK IP
// (localhost is the phone itself!): e.g. http://192.168.1.34:8000

import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { Platform } from 'react-native';

// On web the default is the backend on the machine serving the page (localhost:8000).
// On a phone (Expo Go): the address in app.json; changeable from the Settings screen.
const DEFAULT_URL =
  Platform.OS === 'web' && typeof window !== 'undefined'
    ? `http://${window.location.hostname}:8000`
    : Constants?.expoConfig?.extra?.apiUrl || 'http://192.168.1.100:8000';

export async function apiUrl() {
  return (await AsyncStorage.getItem('apiUrl')) || DEFAULT_URL;
}

async function request(path, options = {}) {
  const base = await apiUrl();
  const resp = await fetch(`${base}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`API ${resp.status}: ${body.slice(0, 200)}`);
  }
  return resp.json();
}

export const api = {
  register: (profile) =>
    request('/api/register', { method: 'POST', body: JSON.stringify({ profile }) }),
  profile: (id) => request(`/api/profile/${id}`),
  updateProfile: (id, profile) =>
    request(`/api/profile/${id}`, { method: 'PUT', body: JSON.stringify(profile) }),
  plan: (id, day = 'today') => request(`/api/plan/${id}?day=${day}`),
  weatherCheck: ({ lat, lon, panel_kw = 5, day = 'today' }) =>
    request(`/api/weather-check?lat=${lat}&lon=${lon}&panel_kw=${panel_kw}&day=${day}`),
  assistant: (user_id, message) =>
    request('/api/assistant', { method: 'POST', body: JSON.stringify({ user_id, message }) }),
  feedback: (body) =>
    request('/api/feedback', { method: 'POST', body: JSON.stringify(body) }),
  report: (id, month) => request(`/api/report/${id}${month ? `?month=${month}` : ''}`),
  notifications: (id) => request(`/api/notifications/${id}`),
  deviceCatalog: () => request('/api/device-catalog'),
};

// Render the saving range readably: if the ends collapse when rounded ("1–1 TL")
// show a single value.
export function rangeTL(min, max) {
  const a = min.toFixed(0);
  const b = max.toFixed(0);
  return a === b ? `~${max.toFixed(1)} TL` : `${a}–${b} TL`;
}

// User-facing reason text is Turkish (shown in the UI).
export const REASON_TEXT = {
  solar_surplus: 'Güneş üretimi bu saatte tüketimi karşılıyor',
  avoid_peak: '17-22 puant diliminden kaçınıyoruz',
  cheap_night: 'Gece tarifesi en ucuz dilim',
  netmeter_edge: 'Evde tüketmek şebekeye satmaktan kârlı',
};
