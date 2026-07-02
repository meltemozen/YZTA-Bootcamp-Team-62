// Backend API istemcisi.
// BASE_URL öncelik sırası: Ayarlar ekranında kaydedilen adres → app.json extra.
// Expo Go ile telefonda test ederken bilgisayarın YEREL AĞ IP'sini kullanın
// (localhost telefonun kendisidir!): örn. http://192.168.1.34:8000

import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { Platform } from 'react-native';

// Web'de varsayılan: sayfanın açıldığı makinedeki backend (localhost:8000).
// Telefonda (Expo Go): app.json'daki adres; Ayarlar ekranından değiştirilebilir.
const VARSAYILAN_URL =
  Platform.OS === 'web' && typeof window !== 'undefined'
    ? `http://${window.location.hostname}:8000`
    : Constants?.expoConfig?.extra?.apiUrl || 'http://192.168.1.100:8000';

export async function apiUrl() {
  return (await AsyncStorage.getItem('apiUrl')) || VARSAYILAN_URL;
}

async function istek(yol, secenekler = {}) {
  const taban = await apiUrl();
  const yanit = await fetch(`${taban}${yol}`, {
    headers: { 'Content-Type': 'application/json' },
    ...secenekler,
  });
  if (!yanit.ok) {
    const govde = await yanit.text();
    throw new Error(`API ${yanit.status}: ${govde.slice(0, 200)}`);
  }
  return yanit.json();
}

export const api = {
  kayit: (profil) =>
    istek('/api/kayit', { method: 'POST', body: JSON.stringify({ profil }) }),
  profil: (id) => istek(`/api/profil/${id}`),
  profilGuncelle: (id, profil) =>
    istek(`/api/profil/${id}`, { method: 'PUT', body: JSON.stringify(profil) }),
  plan: (id, gun = 'bugun') => istek(`/api/plan/${id}?gun=${gun}`),
  asistan: (kullanici_id, mesaj) =>
    istek('/api/asistan', { method: 'POST', body: JSON.stringify({ kullanici_id, mesaj }) }),
  geribildirim: (govde) =>
    istek('/api/geribildirim', { method: 'POST', body: JSON.stringify(govde) }),
  rapor: (id, ay) => istek(`/api/rapor/${id}${ay ? `?ay=${ay}` : ''}`),
  bildirimler: (id) => istek(`/api/bildirimler/${id}`),
  cihazReferans: () => istek('/api/cihaz-referans'),
};

// Tasarruf aralığını okunur yaz: yuvarlanınca uçlar eşitleşiyorsa ("1–1 TL")
// tek değer göster.
export function aralikTL(min, max) {
  const a = min.toFixed(0);
  const u = max.toFixed(0);
  return a === u ? `~${max.toFixed(1)} TL` : `${a}–${u} TL`;
}

export const GEREKCE_METNI = {
  gunes_bol: 'Güneş üretimi bu saatte tüketimi karşılıyor',
  puant_kacinma: '17-22 puant diliminden kaçınıyoruz',
  gece_ucuz: 'Gece tarifesi en ucuz dilim',
  mahsup_avantaji: 'Evde tüketmek şebekeye satmaktan kârlı',
};
