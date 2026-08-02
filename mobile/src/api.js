// Backend API client with JWT authentication.

import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { NativeModules, Platform } from 'react-native';

function cleanUrl(value) {
  return String(value || '').trim().replace(/\/+$/, '');
}

function hostFromUri(value) {
  const text = String(value || '').trim();
  if (!text) return '';

  const withoutScheme = text.replace(/^[a-z][a-z0-9+.-]*:\/\//i, '');
  const host = withoutScheme
    .split('/')[0]
    .split('?')[0]
    .replace(/^\[/, '')
    .split(']')[0]
    .split(':')[0];

  return host;
}

function isLoopback(host) {
  return host === 'localhost' || host === '127.0.0.1' || host === '::1';
}

function isLoopbackUrl(value) {
  return isLoopback(hostFromUri(value));
}

function expoGoHost() {
  const candidates = [
    Constants?.expoConfig?.hostUri,
    Constants?.manifest?.debuggerHost,
    Constants?.manifest?.hostUri,
    Constants?.manifest2?.extra?.expoClient?.hostUri,
    Constants?.linkingUri,
    Constants?.experienceUrl,
    NativeModules?.SourceCode?.scriptURL,
  ];

  for (const value of candidates) {
    const host = hostFromUri(value);
    if (host && !isLoopback(host)) return host;
  }

  return '';
}

function defaultApiUrl() {
  const configured = cleanUrl(Constants?.expoConfig?.extra?.apiUrl);

  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    return configured || `http://${window.location.hostname}:8000`;
  }

  if (__DEV__) {
    const host = expoGoHost();
    if (host && (!configured || isLoopbackUrl(configured))) {
      return `http://${host}:8000`;
    }
  }

  return configured;
}

const DEFAULT_URL = defaultApiUrl();

export async function apiUrl() {
  return DEFAULT_URL;
}

// --- Token storage helpers ---

const TOKEN_KEYS = {
  access: 'auth_access_token',
  refresh: 'auth_refresh_token',
};

export async function getAccessToken() {
  return AsyncStorage.getItem(TOKEN_KEYS.access);
}

export async function getRefreshToken() {
  return AsyncStorage.getItem(TOKEN_KEYS.refresh);
}

export async function saveTokens(accessToken, refreshToken) {
  await AsyncStorage.multiSet([
    [TOKEN_KEYS.access, accessToken],
    [TOKEN_KEYS.refresh, refreshToken],
  ]);
}

export async function clearTokens() {
  await AsyncStorage.multiRemove([
    TOKEN_KEYS.access, TOKEN_KEYS.refresh,
    'userId', 'userName', 'userEmail',
  ]);
}

// --- Core request function with auth ---

// Callback set by AuthContext to trigger logout on 401
let _onAuthExpired = null;
export function setOnAuthExpired(cb) { _onAuthExpired = cb; }

async function request(path, options = {}) {
  const base = await apiUrl();
  if (!base) {
    throw new Error(
      'Bağlantı yapılandırması eksik. Lütfen uygulamayı güncelleyin.'
    );
  }
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };

  // Attach Bearer token if available and not explicitly skipped
  if (!options._skipAuth) {
    const token = await getAccessToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const resp = await fetch(`${base}${path}`, { ...options, headers });

  // Attempt token refresh on 401
  if (resp.status === 401 && !options._skipAuth && !options._isRetry) {
    const refreshed = await _tryRefresh();
    if (refreshed) {
      // Retry the original request with the new token
      return request(path, { ...options, _isRetry: true });
    }
    // Refresh failed — trigger logout
    if (_onAuthExpired) _onAuthExpired();
  }

  if (!resp.ok) {
    let detail = '';
    try {
      detail = (await resp.json())?.detail || '';
    } catch {
      detail = '';
    }
    const error = new Error(detail || `İstek tamamlanamadı (${resp.status}).`);
    error.status = resp.status;
    throw error;
  }
  return resp.json();
}

async function _tryRefresh() {
  try {
    const refreshToken = await getRefreshToken();
    if (!refreshToken) return false;

    const base = await apiUrl();
    const resp = await fetch(`${base}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!resp.ok) return false;

    const body = await resp.json();
    await saveTokens(body.access_token, body.refresh_token);
    return true;
  } catch {
    return false;
  }
}

// --- API methods ---

export const api = {
  // Auth endpoints (no token needed for login/register)
  authRegister: (email, password, name) =>
    request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
      _skipAuth: true,
    }),
  authLogin: (email, password) =>
    request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
      _skipAuth: true,
    }),
  authRefresh: (refresh_token) =>
    request('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token }),
      _skipAuth: true,
    }),
  authMe: () => request('/api/auth/me'),
  authUpdateMe: (data) =>
    request('/api/auth/me', { method: 'PUT', body: JSON.stringify(data) }),
  authChangePassword: (current_password, new_password) =>
    request('/api/auth/password', {
      method: 'PUT',
      body: JSON.stringify({ current_password, new_password }),
    }),

  // Legacy register (backward-compat)
  register: (profile) =>
    request('/api/register', { method: 'POST', body: JSON.stringify({ profile }), _skipAuth: true }),

  // Protected endpoints
  profile: (id) => request(`/api/profile/${id}`),
  updateProfile: (id, profile) =>
    request(`/api/profile/${id}`, { method: 'PUT', body: JSON.stringify(profile) }),
  plan: (id, day = 'today') => request(`/api/plan/${id}?day=${day}`),
  weatherCheck: ({ lat, lon, panel_kw = 5, day = 'today' }) =>
    request(`/api/weather-check?lat=${lat}&lon=${lon}&panel_kw=${panel_kw}&day=${day}`, { _skipAuth: true }),
  assistant: (user_id, message) =>
    request('/api/assistant', { method: 'POST', body: JSON.stringify({ user_id, message }) }),
  feedback: (body) =>
    request('/api/feedback', { method: 'POST', body: JSON.stringify(body) }),
  report: (id, month) => request(`/api/report/${id}${month ? `?month=${month}` : ''}`),
  notifications: (id) => request(`/api/notifications/${id}`),
  deviceCatalog: () => request('/api/device-catalog', { _skipAuth: true }),
  resolveLocation: (province, district) =>
    request(`/api/locations/resolve?province=${encodeURIComponent(province)}&district=${encodeURIComponent(district)}`),
  reverseLocation: (lat, lon) =>
    request(`/api/locations/reverse?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`),
};

// Render the saving range readably: if the ends collapse when rounded ("1–1 TL")
// show a single value.
export function rangeTL(min, max) {
  if (Math.abs(min) < 0.005 && Math.abs(max) < 0.005) return '0 TL';
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
