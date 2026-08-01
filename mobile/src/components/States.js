// Shared screen states: loading, error, empty, and inline notices.
// One place so every screen fails the same way — the user always sees what
// happened and what they can do next, never a blank screen or a raw stack.

import React from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';
import { spacing, font, card, colors, text } from '../theme';

// Minimum comfortable touch target (iOS HIG 44pt / Android 48dp).
export const TOUCH = 44;

/** Skeleton block — keeps layout stable while data loads. */
function Shimmer({ height, width = '100%', radius = 10 }) {
  return (
    <View style={{
      height, width, borderRadius: radius,
      backgroundColor: colors.raised, marginBottom: spacing.s,
    }} />
  );
}

/** Loading placeholder. `variant="plan"` mimics the Today layout so the screen
 *  does not jump when the real content arrives. */
export function LoadingState({ label = 'Yükleniyor…', variant }) {
  if (variant === 'plan') {
    return (
      <View accessibilityLabel={label} accessibilityRole="progressbar">
        <Shimmer height={132} radius={18} />
        <View style={card}><Shimmer height={150} /></View>
        <Shimmer height={72} radius={16} />
        <Shimmer height={72} radius={16} />
      </View>
    );
  }
  return (
    <View style={{ alignItems: 'center', marginTop: spacing.xl, gap: spacing.s }}
          accessibilityRole="progressbar" accessibilityLabel={label}>
      <ActivityIndicator color={colors.amber} />
      <Text style={text.small}>{label}</Text>
    </View>
  );
}

/** Something failed. Always says what happened AND offers a way forward. */
export function ErrorState({ title = 'Bağlantı kurulamadı', message, hint, onRetry,
                             retryLabel = 'Tekrar dene' }) {
  return (
    <View style={[card, { borderColor: colors.critical }]}
          accessibilityRole="alert">
      <Text style={[text.subtitle, { color: colors.critical }]}>{title}</Text>
      {message ? (
        <Text style={[text.body, { marginTop: 6 }]}>{message}</Text>
      ) : null}
      {hint ? (
        <Text style={[text.small, { marginTop: 6, lineHeight: 17 }]}>{hint}</Text>
      ) : null}
      {onRetry ? (
        <Pressable
          onPress={onRetry}
          accessibilityRole="button"
          accessibilityLabel={retryLabel}
          style={{
            marginTop: spacing.m, minHeight: TOUCH, borderRadius: 12,
            borderWidth: 1, borderColor: colors.amber,
            alignItems: 'center', justifyContent: 'center',
          }}
        >
          <Text style={{ color: colors.amber, fontFamily: font.semibold, fontSize: 14 }}>
            {retryLabel}
          </Text>
        </Pressable>
      ) : null}
    </View>
  );
}

/** Nothing to show yet — explains why and what to do, never just "boş". */
export function EmptyState({ title, message, actionLabel, onAction }) {
  return (
    <View style={card}>
      <Text style={text.subtitle}>{title}</Text>
      <Text style={[text.body, { marginTop: 6 }]}>{message}</Text>
      {actionLabel && onAction ? (
        <Pressable
          onPress={onAction}
          accessibilityRole="button"
          accessibilityLabel={actionLabel}
          style={{
            marginTop: spacing.m, minHeight: TOUCH, borderRadius: 12,
            borderWidth: 1, borderColor: colors.border,
            alignItems: 'center', justifyContent: 'center',
          }}
        >
          <Text style={{ color: colors.ink, fontFamily: font.semibold, fontSize: 14 }}>
            {actionLabel}
          </Text>
        </Pressable>
      ) : null}
    </View>
  );
}

/** Inline note. `tone="warn"` for data-quality caveats. */
export function Notice({ children, tone = 'info' }) {
  const accent = tone === 'warn' ? colors.amber : colors.border;
  return (
    <View
      accessibilityRole="alert"
      style={[card, {
        borderLeftWidth: 3, borderLeftColor: accent,
        paddingVertical: 12, marginBottom: spacing.s,
      }]}
    >
      <Text style={[text.small, { lineHeight: 18, color: colors.inkSecondary }]}>
        {children}
      </Text>
    </View>
  );
}

// How the weather that a plan rests on was obtained. "live" needs no caveat;
// the other two mean the forecast is a fallback and the user deserves to know.
const WEATHER_CAVEAT = {
  cached: 'Hava servisine şu an ulaşılamıyor — plan en son alınan tahminle kuruldu. ' +
          'Bağlantı gelince yenile.',
  synthetic: 'Hava servisine ulaşılamadı ve önbellek boştu — plan mevsim ortalamasına ' +
             'dayalı tahmini bir güneş eğrisiyle kuruldu. Gerçek üretim farklı olabilir.',
};

/** Warns only when the plan does NOT rest on a live forecast. */
export function DataQualityNotice({ weatherSource }) {
  const caveat = WEATHER_CAVEAT[weatherSource];
  if (!caveat) return null;
  return <Notice tone="warn">{caveat}</Notice>;
}
