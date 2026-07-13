// Wattra brand elements: logo mark (sun ring + bolt) and wordmark.
// The logo is a single SVG — the same mark is used for the app icon, splash
// and headers.

import React from 'react';
import { Text, View } from 'react-native';
import Svg, { Circle, Defs, LinearGradient, Path, Stop } from 'react-native-svg';
import { colors, font } from '../theme';

export function LogoMark({ size = 34 }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 48 48">
      <Defs>
        <LinearGradient id="amber" x1="0" y1="0" x2="1" y2="1">
          <Stop offset="0" stopColor={colors.amber} />
          <Stop offset="1" stopColor={colors.amberDark} />
        </LinearGradient>
      </Defs>
      {/* Sun ring — small gap at the top (rising sun) */}
      <Circle
        cx="24" cy="24" r="19"
        stroke="url(#amber)" strokeWidth="4" fill="none"
        strokeDasharray="100 20" strokeDashoffset="-8" strokeLinecap="round"
      />
      {/* Bolt */}
      <Path
        d="M26.5 12 L17 26.5 h6 L21.5 36 L31 21.5 h-6 Z"
        fill="url(#amber)"
      />
    </Svg>
  );
}

export function Wordmark({ size = 24 }) {
  return (
    <Text style={{ fontFamily: font.title, fontSize: size, color: colors.ink, letterSpacing: 0.5 }}>
      watt<Text style={{ color: colors.amber }}>ra</Text>
    </Text>
  );
}

/** Screen-top header strip: small logo + screen name. */
export function ScreenHeader({ title, right }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 18 }}>
      <LogoMark size={26} />
      <Text style={{
        fontFamily: font.title, fontSize: 22, color: colors.ink,
        marginLeft: 10, flex: 1, letterSpacing: 0.2,
      }}>
        {title}
      </Text>
      {right}
    </View>
  );
}
