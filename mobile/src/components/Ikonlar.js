// SVG ikon seti — emoji yerine tutarlı, tek kalınlıkta çizgi ikonları.
// Hepsi 24×24 viewBox, 1.8 kalınlık, yuvarlak uçlar.

import React from 'react';
import Svg, { Circle, Line, Path, Rect } from 'react-native-svg';

const S = ({ children, boyut, renk }) => (
  <Svg width={boyut} height={boyut} viewBox="0 0 24 24" fill="none"
       stroke={renk} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    {children}
  </Svg>
);

export const SimsekIkon = ({ boyut = 22, renk = '#fff', dolu = false }) => (
  <Svg width={boyut} height={boyut} viewBox="0 0 24 24"
       fill={dolu ? renk : 'none'} stroke={renk} strokeWidth={1.8}
       strokeLinecap="round" strokeLinejoin="round">
    <Path d="M13 2 L5 13.5 h5.5 L11 22 l8-11.5 h-5.5 Z" />
  </Svg>
);

export const SohbetIkon = ({ boyut = 22, renk = '#fff' }) => (
  <S boyut={boyut} renk={renk}>
    <Path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.3 8.9 8.9 0 0 1-3.2-.6L3 21l1.9-5.4a8.1 8.1 0 0 1-.9-3.6A8.4 8.4 0 0 1 12.5 3.2 8.4 8.4 0 0 1 21 11.5Z" />
  </S>
);

export const GrafikIkon = ({ boyut = 22, renk = '#fff' }) => (
  <S boyut={boyut} renk={renk}>
    <Line x1="4" y1="20" x2="20" y2="20" />
    <Rect x="6" y="12" width="3.2" height="8" rx="1" />
    <Rect x="11" y="7" width="3.2" height="13" rx="1" />
    <Rect x="16" y="10" width="3.2" height="10" rx="1" />
  </S>
);

export const AyarIkon = ({ boyut = 22, renk = '#fff' }) => (
  <S boyut={boyut} renk={renk}>
    <Line x1="4" y1="7" x2="20" y2="7" />
    <Circle cx="9" cy="7" r="2.2" fill="none" />
    <Line x1="4" y1="17" x2="20" y2="17" />
    <Circle cx="15" cy="17" r="2.2" fill="none" />
  </S>
);

export const GunesIkon = ({ boyut = 22, renk = '#fff' }) => (
  <S boyut={boyut} renk={renk}>
    <Circle cx="12" cy="12" r="4" />
    <Line x1="12" y1="2.5" x2="12" y2="5" />
    <Line x1="12" y1="19" x2="12" y2="21.5" />
    <Line x1="2.5" y1="12" x2="5" y2="12" />
    <Line x1="19" y1="12" x2="21.5" y2="12" />
    <Line x1="5.3" y1="5.3" x2="7" y2="7" />
    <Line x1="17" y1="17" x2="18.7" y2="18.7" />
    <Line x1="5.3" y1="18.7" x2="7" y2="17" />
    <Line x1="17" y1="7" x2="18.7" y2="5.3" />
  </S>
);

export const BataryaIkon = ({ boyut = 22, renk = '#fff' }) => (
  <S boyut={boyut} renk={renk}>
    <Rect x="3" y="8" width="16" height="9" rx="2" />
    <Line x1="21.5" y1="11" x2="21.5" y2="14" />
    <Path d="M11.5 9.5 L8.5 12.8 h2.5 L10 15.5 l3-3.3 h-2.5 Z" strokeWidth={1.4} />
  </S>
);

export const PrizIkon = ({ boyut = 22, renk = '#fff' }) => (
  <S boyut={boyut} renk={renk}>
    {/* Fiş: iki uç + gövde + kablo */}
    <Line x1="9" y1="2.5" x2="9" y2="7" />
    <Line x1="15" y1="2.5" x2="15" y2="7" />
    <Path d="M6.5 7 h11 v3.5 a5.5 5.5 0 0 1-11 0 Z" />
    <Line x1="12" y1="16" x2="12" y2="21.5" />
  </S>
);

export const YaprakIkon = ({ boyut = 22, renk = '#fff' }) => (
  <S boyut={boyut} renk={renk}>
    <Path d="M5 20 C5 10 11 4.5 20 4 c.5 9-5 15.5-14.5 16Z" />
    <Path d="M5 20 C8 15 12 11 17 8" />
  </S>
);

export const ZilIkon = ({ boyut = 22, renk = '#fff' }) => (
  <S boyut={boyut} renk={renk}>
    <Path d="M18 9.5 a6 6 0 0 0-12 0 c0 5-2 6.5-2 6.5 h16 s-2-1.5-2-6.5" />
    <Path d="M10 19.5 a2.2 2.2 0 0 0 4 0" />
  </S>
);
