// Voltaic marka öğeleri: logo işareti (güneş halkası + şimşek) ve söz markası.
// Logo tek SVG'dir — uygulama ikonu, açılış ve başlıklarda aynı işaret kullanılır.

import React from 'react';
import { Text, View } from 'react-native';
import Svg, { Circle, Defs, LinearGradient, Path, Stop } from 'react-native-svg';
import { font, renk } from '../theme';

export function LogoIsareti({ boyut = 34 }) {
  return (
    <Svg width={boyut} height={boyut} viewBox="0 0 48 48">
      <Defs>
        <LinearGradient id="amber" x1="0" y1="0" x2="1" y2="1">
          <Stop offset="0" stopColor={renk.amber} />
          <Stop offset="1" stopColor={renk.amberKoyu} />
        </LinearGradient>
      </Defs>
      {/* Güneş halkası — üstte küçük boşluk (doğan güneş) */}
      <Circle
        cx="24" cy="24" r="19"
        stroke="url(#amber)" strokeWidth="4" fill="none"
        strokeDasharray="100 20" strokeDashoffset="-8" strokeLinecap="round"
      />
      {/* Şimşek */}
      <Path
        d="M26.5 12 L17 26.5 h6 L21.5 36 L31 21.5 h-6 Z"
        fill="url(#amber)"
      />
    </Svg>
  );
}

export function SozMarkasi({ boyut = 24 }) {
  return (
    <Text style={{ fontFamily: font.baslik, fontSize: boyut, color: renk.murekkep, letterSpacing: 0.5 }}>
      volta<Text style={{ color: renk.amber }}>ic</Text>
    </Text>
  );
}

/** Ekran üstü başlık şeridi: küçük logo + ekran adı. */
export function EkranBasligi({ baslik, sag }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 18 }}>
      <LogoIsareti boyut={26} />
      <Text style={{
        fontFamily: font.baslik, fontSize: 22, color: renk.murekkep,
        marginLeft: 10, flex: 1, letterSpacing: 0.2,
      }}>
        {baslik}
      </Text>
      {sag}
    </View>
  );
}
