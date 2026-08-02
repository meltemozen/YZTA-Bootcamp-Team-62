// Shared screen states: loading, error, empty, and inline notices.
// One place so every screen fails the same way — the user always sees what
// happened and what they can do next, never a blank screen or a raw stack.

import React, { useEffect, useRef } from 'react';
import { ActivityIndicator, Animated, Pressable, Text, View } from 'react-native';
import { spacing, font, card, colors, text } from '../theme';

// Minimum comfortable touch target (iOS HIG 44pt / Android 48dp).
export const TOUCH = 44;

const NOTICE_COLORS = {
  info: colors.amber,
  success: colors.success,
  error: colors.critical,
};

/** Compact animated feedback for actions that complete in place. */
export function InlineNotice({
  tone = 'info', message, loading = false, actionLabel, onAction,
}) {
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    progress.setValue(0);
    Animated.timing(progress, {
      toValue: 1,
      duration: 180,
      useNativeDriver: true,
    }).start();
  }, [message, progress]);

  if (!message) return null;
  const accent = NOTICE_COLORS[tone] || NOTICE_COLORS.info;

  return (
    <Animated.View
      accessibilityRole={tone === 'error' ? 'alert' : 'text'}
      accessibilityLiveRegion="polite"
      style={{
        opacity: progress,
        transform: [{
          translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [5, 0] }),
        }],
        flexDirection: 'row', alignItems: 'center', gap: spacing.s,
        borderWidth: 1, borderColor: accent, borderRadius: 10,
        backgroundColor: colors.input, paddingHorizontal: spacing.m,
        paddingVertical: spacing.s, marginBottom: spacing.m,
      }}
    >
      {loading ? (
        <ActivityIndicator color={accent} size="small" />
      ) : (
        <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: accent }} />
      )}
      <Text style={[text.small, { color: colors.ink, flex: 1, lineHeight: 18 }]}>
        {message}
      </Text>
      {actionLabel && onAction ? (
        <Pressable
          onPress={onAction}
          accessibilityRole="button"
          accessibilityLabel={actionLabel}
          style={{ minHeight: TOUCH, justifyContent: 'center', paddingHorizontal: spacing.xs }}
        >
          <Text style={{ color: accent, fontFamily: font.semibold, fontSize: 13 }}>
            {actionLabel}
          </Text>
        </Pressable>
      ) : null}
    </Animated.View>
  );
}

/** Last-resort UI guard so a render failure never leaves a blank screen. */
export class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <View style={{ flex: 1, justifyContent: 'center', padding: spacing.l, backgroundColor: colors.page }}>
        <ErrorState
          title="Bir sorun oluştu"
          message="Bu ekran beklenmedik şekilde kapanmak üzereydi. Bilgilerin kaybolmadı."
          onRetry={() => this.setState({ failed: false })}
        />
      </View>
    );
  }
}

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
