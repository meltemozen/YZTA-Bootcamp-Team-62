// ─── Voltaic Tasarım Kimliği ────────────────────────────────────────────────
// "Gece şebekesi" koyu tema: derin lacivert zemin + güneş amberi vurgu.
// Tipografi: Space Grotesk (başlık/rakam) + Inter (gövde).
//
// Grafik seri renkleri (uretim/tuketim) dataviz CVD validatöründen
// #151b2b yüzeyi için geçirilmiştir — değiştirilirse yeniden doğrulanmalı.
// UI vurgu amberi (amber) daha parlaktır; yalnız buton/marka içindir,
// grafik serisi olarak KULLANILMAZ.

export const renk = {
  // Zemin katmanları (koyudan açığa)
  sayfa: '#0b0f1a',
  yuzey: '#151b2b',
  yukseltilmis: '#1c2438',
  girdi: '#101625',

  // Mürekkep
  murekkep: '#f4f6fb',
  murekkepIkincil: '#a8b0c2',
  soluk: '#6b7488',
  cizgi: 'rgba(255,255,255,0.07)',
  kenar: 'rgba(255,255,255,0.08)',

  // Marka
  amber: '#f7b32b',          // birincil aksiyon / vurgu
  amberKoyu: '#ee8f1f',      // gradyan alt ucu
  amberUstuMurekkep: '#221500', // amber zemin üstü metin
  amberYumusak: 'rgba(247,179,43,0.12)', // seçili çip / rozet zemini

  // Grafik serileri (validatörden geçti — dokunma)
  uretim: '#c98500',
  tuketim: '#3987e5',
  vurgu: '#f7b32b',

  // Tarife bantları (fiyat büyüklüğü → beyaz örtü yoğunluğu)
  bantGece: 'transparent',
  bantGunduz: 'rgba(255,255,255,0.045)',
  bantPuant: 'rgba(255,255,255,0.10)',

  // Durum
  iyi: '#2fbf66',
  iyiMetin: '#7be0a2',
  iyiZemin: 'rgba(47,191,102,0.14)',
  kritik: '#f26d6d',
};

export const bosluk = { xs: 4, s: 8, m: 16, l: 24, xl: 32 };

export const font = {
  baslik: 'SpaceGrotesk_700Bold',
  rakam: 'SpaceGrotesk_500Medium',
  govde: 'Inter_400Regular',
  orta: 'Inter_500Medium',
  kalin: 'Inter_600SemiBold',
};

export const yazi = {
  ekranBaslik: { fontSize: 24, fontFamily: font.baslik, color: renk.murekkep, letterSpacing: 0.2 },
  baslik: { fontSize: 21, fontFamily: font.baslik, color: renk.murekkep },
  altBaslik: { fontSize: 15.5, fontFamily: font.kalin, color: renk.murekkep },
  govde: { fontSize: 14.5, fontFamily: font.govde, color: renk.murekkepIkincil, lineHeight: 21 },
  kucuk: { fontSize: 12, fontFamily: font.govde, color: renk.soluk },
  etiket: { fontSize: 11, fontFamily: font.kalin, color: renk.soluk, letterSpacing: 1.2, textTransform: 'uppercase' },
  buyukSayi: { fontSize: 36, fontFamily: font.baslik, color: renk.murekkep, letterSpacing: -0.5 },
};

export const kart = {
  backgroundColor: renk.yuzey,
  borderRadius: 16,
  borderWidth: 1,
  borderColor: renk.kenar,
  padding: bosluk.m,
  marginBottom: bosluk.m,
};

export const birincilButon = {
  backgroundColor: renk.amber,
  borderRadius: 14,
  paddingVertical: 15,
  paddingHorizontal: 28,
  alignItems: 'center',
};

export const birincilButonMetin = {
  color: renk.amberUstuMurekkep,
  fontFamily: font.kalin,
  fontSize: 16,
};
