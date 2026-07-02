// 24 saatlik üretim/tüketim grafiği — react-native-svg ile.
//
// Tasarım kuralları (dataviz yöntemi):
// * Tek y ekseni (kWh) — iki seri aynı birimde, çift eksen YOK.
// * Üretim: sarı alan + 2px çizgi; Tüketim: mavi 2px çizgi. Palet CVD
//   validatöründen geçti; sarının yüzey kontrastı düşük olduğu için seriler
//   DOĞRUDAN etiketlenir (relief kuralı) + lejant her zaman görünür.
// * Tarife dilimleri fiyat büyüklüğüdür → tek ton gri bantlar (açık→koyu).
// * Dokunmatik inceleme: parmakla kaydırınca saat kılavuzu + değer kutusu.

import React, { useMemo, useState } from 'react';
import { Text as RNText, View } from 'react-native';
import Svg, { Line, Path, Rect, Text as SvgText } from 'react-native-svg';
import { bosluk, renk, yazi } from '../theme';

const H = 190;
const KENAR = { sol: 30, sag: 8, ust: 22, alt: 20 };

function yol(veri, olcekX, olcekY, kapali = false) {
  const parcalar = veri.map(
    (v, i) => `${i === 0 ? 'M' : 'L'}${olcekX(i).toFixed(1)},${olcekY(v).toFixed(1)}`
  );
  if (kapali) {
    parcalar.push(`L${olcekX(veri.length - 1).toFixed(1)},${olcekY(0).toFixed(1)}`);
    parcalar.push(`L${olcekX(0).toFixed(1)},${olcekY(0).toFixed(1)}Z`);
  }
  return parcalar.join(' ');
}

export default function GunlukGrafik({ uretim, tuketim, dilim }) {
  const [genislik, setGenislik] = useState(0);
  const [secili, setSecili] = useState(null); // incelenen saat (0-23) | null

  const { olcekX, olcekY, maks } = useMemo(() => {
    const m = Math.max(...uretim, ...tuketim, 0.1);
    const icW = Math.max(genislik - KENAR.sol - KENAR.sag, 1);
    const icH = H - KENAR.ust - KENAR.alt;
    return {
      maks: m,
      olcekX: (saat) => KENAR.sol + (saat / 23) * icW,
      olcekY: (v) => KENAR.ust + icH * (1 - v / m),
    };
  }, [uretim, tuketim, genislik]);

  // Ardışık aynı-dilim saatlerini bant dikdörtgenlerine grupla
  const bantlar = useMemo(() => {
    const sonuc = [];
    let bas = 0;
    for (let s = 1; s <= 24; s++) {
      if (s === 24 || dilim[s] !== dilim[bas]) {
        sonuc.push({ dilim: dilim[bas], bas, son: s - 1 });
        bas = s;
      }
    }
    return sonuc;
  }, [dilim]);

  const bantRengi = { gunduz: renk.bantGunduz, puant: renk.bantPuant, gece: renk.bantGece, tek: renk.bantGece };
  const bantAdi = { gunduz: 'gündüz', puant: 'puant', gece: 'gece' };

  const dokunma = (e) => {
    if (!genislik) return;
    // locationX: native; web'de responder olayı offsetX taşır
    const x = e.nativeEvent.locationX ?? e.nativeEvent.offsetX ?? 0;
    const saat = Math.round(((x - KENAR.sol) / (genislik - KENAR.sol - KENAR.sag)) * 23);
    setSecili(Math.min(23, Math.max(0, saat)));
  };

  return (
    <View onLayout={(e) => setGenislik(e.nativeEvent.layout.width)}>
      {/* Lejant: renk çipi + metin belirteci (metin asla seri renginde değil) */}
      <View style={{ flexDirection: 'row', gap: bosluk.m, marginBottom: bosluk.s }}>
        {[['Üretim', renk.uretim], ['Tüketim', renk.tuketim]].map(([ad, r]) => (
          <View key={ad} style={{ flexDirection: 'row', alignItems: 'center', gap: 5 }}>
            <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: r }} />
            <RNText style={yazi.kucuk}>{ad} (kWh)</RNText>
          </View>
        ))}
      </View>

      {genislik > 0 && (
        <Svg
          width={genislik}
          height={H}
          onStartShouldSetResponder={() => true}
          onMoveShouldSetResponder={() => true}
          onResponderGrant={dokunma}
          onResponderMove={dokunma}
          onResponderRelease={() => setSecili(null)}
        >
          {/* Tarife bantları (arka plan, fiyat büyüklüğü = gri tonu) */}
          {bantlar.map((b, i) =>
            bantRengi[b.dilim] === 'transparent' ? null : (
              <Rect
                key={i}
                x={olcekX(b.bas)}
                y={KENAR.ust}
                width={olcekX(b.son) - olcekX(b.bas) + (genislik - KENAR.sol - KENAR.sag) / 23}
                height={H - KENAR.ust - KENAR.alt}
                fill={bantRengi[b.dilim]}
              />
            )
          )}
          {bantlar.map((b, i) =>
            bantAdi[b.dilim] && b.son - b.bas >= 3 ? (
              <SvgText
                key={`e${i}`}
                x={(olcekX(b.bas) + olcekX(b.son)) / 2}
                y={KENAR.ust - 8}
                fontSize="9"
                fill={renk.soluk}
                textAnchor="middle"
              >
                {bantAdi[b.dilim]}
              </SvgText>
            ) : null
          )}

          {/* Izgara: yatay 3 ince çizgi + y etiketleri */}
          {[0, 0.5, 1].map((t) => (
            <React.Fragment key={t}>
              <Line
                x1={KENAR.sol}
                x2={genislik - KENAR.sag}
                y1={olcekY(maks * t)}
                y2={olcekY(maks * t)}
                stroke={renk.cizgi}
                strokeWidth={1}
              />
              <SvgText x={KENAR.sol - 4} y={olcekY(maks * t) + 3} fontSize="9"
                       fill={renk.soluk} textAnchor="end">
                {(maks * t).toFixed(t === 0 ? 0 : 1)}
              </SvgText>
            </React.Fragment>
          ))}

          {/* Seriler: üretim alan+çizgi, tüketim çizgi */}
          <Path d={yol(uretim, olcekX, olcekY, true)} fill={renk.uretim} opacity={0.22} />
          <Path d={yol(uretim, olcekX, olcekY)} stroke={renk.uretim} strokeWidth={2} fill="none" />
          <Path d={yol(tuketim, olcekX, olcekY)} stroke={renk.tuketim} strokeWidth={2} fill="none" />

          {/* X etiketleri */}
          {[0, 6, 12, 18, 23].map((s) => (
            <SvgText key={s} x={olcekX(s)} y={H - 5} fontSize="9"
                     fill={renk.soluk} textAnchor="middle">
              {String(s).padStart(2, '0')}
            </SvgText>
          ))}

          {/* Dokunmatik inceleme: kılavuz + işaret noktaları */}
          {secili !== null && (
            <>
              <Line x1={olcekX(secili)} x2={olcekX(secili)} y1={KENAR.ust}
                    y2={H - KENAR.alt} stroke={renk.soluk} strokeWidth={1} />
              {[[uretim[secili], renk.uretim], [tuketim[secili], renk.tuketim]].map(([v, r], i) => (
                <React.Fragment key={i}>
                  {/* 2px yüzey halkası: üst üste binen işaretler ayrışsın */}
                  <Rect x={olcekX(secili) - 6} y={olcekY(v) - 6} width={12} height={12}
                        rx={6} fill={renk.yuzey} />
                  <Rect x={olcekX(secili) - 4} y={olcekY(v) - 4} width={8} height={8}
                        rx={4} fill={r} />
                </React.Fragment>
              ))}
            </>
          )}
        </Svg>
      )}

      {/* İnceleme kutusu (SVG dışında, metin belirteçleriyle) */}
      <View style={{ minHeight: 20, alignItems: 'center' }}>
        {secili !== null ? (
          <RNText style={yazi.kucuk}>
            {String(secili).padStart(2, '0')}:00 · Üretim{' '}
            <RNText style={{ color: renk.murekkep, fontWeight: '600' }}>
              {uretim[secili].toFixed(1)}
            </RNText>{' '}
            kWh · Tüketim{' '}
            <RNText style={{ color: renk.murekkep, fontWeight: '600' }}>
              {tuketim[secili].toFixed(1)}
            </RNText>{' '}
            kWh
          </RNText>
        ) : (
          <RNText style={yazi.kucuk}>Değerleri görmek için grafiğe dokun</RNText>
        )}
      </View>
    </View>
  );
}
