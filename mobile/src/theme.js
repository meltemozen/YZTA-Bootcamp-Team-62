// ─── Wattra Design Identity ────────────────────────────────────────────────
// "Night grid" dark theme: deep navy background + solar amber accent.
// Typography: Space Grotesk (titles/numbers) + Inter (body).
//
// Chart series colors (production/consumption) passed a CVD (color-blindness)
// validator against the #151b2b surface — re-validate if changed.
// The UI accent amber (amber) is brighter; it is for buttons/brand ONLY and is
// NOT used as a chart series color.

export const colors = {
  // Background layers (dark → light)
  page: '#0b0f1a',
  surface: '#151b2b',
  raised: '#1c2438',
  input: '#101625',

  // Ink
  ink: '#f4f6fb',
  inkSecondary: '#a8b0c2',
  faint: '#6b7488',
  line: 'rgba(255,255,255,0.07)',
  border: 'rgba(255,255,255,0.08)',

  // Brand
  amber: '#f7b32b',          // primary action / accent
  amberDark: '#ee8f1f',      // gradient bottom
  amberInk: '#221500',       // text on amber background
  amberSoft: 'rgba(247,179,43,0.12)', // selected chip / badge background

  // Chart series (passed the validator — do not touch)
  production: '#c98500',
  consumption: '#3987e5',
  accent: '#f7b32b',

  // Tariff bands (price magnitude → white-overlay density)
  bandNight: 'transparent',
  bandDay: 'rgba(255,255,255,0.045)',
  bandPeak: 'rgba(255,255,255,0.10)',

  // Status
  good: '#2fbf66',
  goodText: '#7be0a2',
  goodBg: 'rgba(47,191,102,0.14)',
  critical: '#f26d6d',
};

export const spacing = { xs: 4, s: 8, m: 16, l: 24, xl: 32 };

export const font = {
  title: 'SpaceGrotesk_700Bold',
  number: 'SpaceGrotesk_500Medium',
  body: 'Inter_400Regular',
  medium: 'Inter_500Medium',
  semibold: 'Inter_600SemiBold',
};

export const text = {
  screenTitle: { fontSize: 24, fontFamily: font.title, color: colors.ink, letterSpacing: 0.2 },
  title: { fontSize: 21, fontFamily: font.title, color: colors.ink },
  subtitle: { fontSize: 15.5, fontFamily: font.semibold, color: colors.ink },
  body: { fontSize: 14.5, fontFamily: font.body, color: colors.inkSecondary, lineHeight: 21 },
  small: { fontSize: 12, fontFamily: font.body, color: colors.faint },
  label: { fontSize: 11, fontFamily: font.semibold, color: colors.faint, letterSpacing: 1.2, textTransform: 'uppercase' },
  bigNumber: { fontSize: 36, fontFamily: font.title, color: colors.ink, letterSpacing: -0.5 },
};

export const card = {
  backgroundColor: colors.surface,
  borderRadius: 16,
  borderWidth: 1,
  borderColor: colors.border,
  padding: spacing.m,
  marginBottom: spacing.m,
};

export const primaryButton = {
  backgroundColor: colors.amber,
  borderRadius: 14,
  paddingVertical: 15,
  paddingHorizontal: 28,
  alignItems: 'center',
};

export const primaryButtonText = {
  color: colors.amberInk,
  fontFamily: font.semibold,
  fontSize: 16,
};
