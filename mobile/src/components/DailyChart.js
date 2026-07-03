// 24-hour production/consumption chart — with react-native-svg.
//
// Design rules (dataviz method):
// * Single y axis (kWh) — both series same unit, NO dual axis.
// * Production: yellow area + 2px line; Consumption: blue 2px line. Palette
//   passed the CVD validator; since yellow has low surface contrast, series are
//   DIRECTLY labeled (relief rule) + the legend is always visible.
// * Tariff bands are price magnitude → single-tone gray bands (light→dark).
// * Touch inspection: dragging shows an hour guide + a value box.

import React, { useMemo, useState } from 'react';
import { Text as RNText, View } from 'react-native';
import Svg, { Line, Path, Rect, Text as SvgText } from 'react-native-svg';
import { colors, spacing, text } from '../theme';

const H = 190;
const MARGIN = { left: 30, right: 8, top: 22, bottom: 20 };

function pathFor(data, scaleX, scaleY, closed = false) {
  const parts = data.map(
    (v, i) => `${i === 0 ? 'M' : 'L'}${scaleX(i).toFixed(1)},${scaleY(v).toFixed(1)}`
  );
  if (closed) {
    parts.push(`L${scaleX(data.length - 1).toFixed(1)},${scaleY(0).toFixed(1)}`);
    parts.push(`L${scaleX(0).toFixed(1)},${scaleY(0).toFixed(1)}Z`);
  }
  return parts.join(' ');
}

export default function DailyChart({ production, consumption, band }) {
  const [width, setWidth] = useState(0);
  const [selected, setSelected] = useState(null); // inspected hour (0-23) | null

  const { scaleX, scaleY, max } = useMemo(() => {
    const m = Math.max(...production, ...consumption, 0.1);
    const innerW = Math.max(width - MARGIN.left - MARGIN.right, 1);
    const innerH = H - MARGIN.top - MARGIN.bottom;
    return {
      max: m,
      scaleX: (hour) => MARGIN.left + (hour / 23) * innerW,
      scaleY: (v) => MARGIN.top + innerH * (1 - v / m),
    };
  }, [production, consumption, width]);

  // Group consecutive same-band hours into band rectangles
  const bands = useMemo(() => {
    const out = [];
    let start = 0;
    for (let h = 1; h <= 24; h++) {
      if (h === 24 || band[h] !== band[start]) {
        out.push({ band: band[start], start, end: h - 1 });
        start = h;
      }
    }
    return out;
  }, [band]);

  const bandColor = { day: colors.bandDay, peak: colors.bandPeak, night: colors.bandNight, flat: colors.bandNight };
  const bandLabel = { day: 'gündüz', peak: 'puant', night: 'gece' };

  const onTouch = (e) => {
    if (!width) return;
    // locationX: native; on web the responder event carries offsetX
    const x = e.nativeEvent.locationX ?? e.nativeEvent.offsetX ?? 0;
    const hour = Math.round(((x - MARGIN.left) / (width - MARGIN.left - MARGIN.right)) * 23);
    setSelected(Math.min(23, Math.max(0, hour)));
  };

  return (
    <View onLayout={(e) => setWidth(e.nativeEvent.layout.width)}>
      {/* Legend: color chip + text marker (text is never in the series color) */}
      <View style={{ flexDirection: 'row', gap: spacing.m, marginBottom: spacing.s }}>
        {[['Üretim', colors.production], ['Tüketim', colors.consumption]].map(([label, c]) => (
          <View key={label} style={{ flexDirection: 'row', alignItems: 'center', gap: 5 }}>
            <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: c }} />
            <RNText style={text.small}>{label} (kWh)</RNText>
          </View>
        ))}
      </View>

      {width > 0 && (
        <Svg
          width={width}
          height={H}
          onStartShouldSetResponder={() => true}
          onMoveShouldSetResponder={() => true}
          onResponderGrant={onTouch}
          onResponderMove={onTouch}
          onResponderRelease={() => setSelected(null)}
        >
          {/* Tariff bands (background, price magnitude = gray tone) */}
          {bands.map((b, i) =>
            bandColor[b.band] === 'transparent' ? null : (
              <Rect
                key={i}
                x={scaleX(b.start)}
                y={MARGIN.top}
                width={scaleX(b.end) - scaleX(b.start) + (width - MARGIN.left - MARGIN.right) / 23}
                height={H - MARGIN.top - MARGIN.bottom}
                fill={bandColor[b.band]}
              />
            )
          )}
          {bands.map((b, i) =>
            bandLabel[b.band] && b.end - b.start >= 3 ? (
              <SvgText
                key={`l${i}`}
                x={(scaleX(b.start) + scaleX(b.end)) / 2}
                y={MARGIN.top - 8}
                fontSize="9"
                fill={colors.faint}
                textAnchor="middle"
              >
                {bandLabel[b.band]}
              </SvgText>
            ) : null
          )}

          {/* Grid: 3 thin horizontal lines + y labels */}
          {[0, 0.5, 1].map((t) => (
            <React.Fragment key={t}>
              <Line
                x1={MARGIN.left}
                x2={width - MARGIN.right}
                y1={scaleY(max * t)}
                y2={scaleY(max * t)}
                stroke={colors.line}
                strokeWidth={1}
              />
              <SvgText x={MARGIN.left - 4} y={scaleY(max * t) + 3} fontSize="9"
                       fill={colors.faint} textAnchor="end">
                {(max * t).toFixed(t === 0 ? 0 : 1)}
              </SvgText>
            </React.Fragment>
          ))}

          {/* Series: production area+line, consumption line */}
          <Path d={pathFor(production, scaleX, scaleY, true)} fill={colors.production} opacity={0.22} />
          <Path d={pathFor(production, scaleX, scaleY)} stroke={colors.production} strokeWidth={2} fill="none" />
          <Path d={pathFor(consumption, scaleX, scaleY)} stroke={colors.consumption} strokeWidth={2} fill="none" />

          {/* X labels */}
          {[0, 6, 12, 18, 23].map((h) => (
            <SvgText key={h} x={scaleX(h)} y={H - 5} fontSize="9"
                     fill={colors.faint} textAnchor="middle">
              {String(h).padStart(2, '0')}
            </SvgText>
          ))}

          {/* Touch inspection: guide + marker dots */}
          {selected !== null && (
            <>
              <Line x1={scaleX(selected)} x2={scaleX(selected)} y1={MARGIN.top}
                    y2={H - MARGIN.bottom} stroke={colors.faint} strokeWidth={1} />
              {[[production[selected], colors.production], [consumption[selected], colors.consumption]].map(([v, c], i) => (
                <React.Fragment key={i}>
                  {/* 2px surface ring: separate overlapping markers */}
                  <Rect x={scaleX(selected) - 6} y={scaleY(v) - 6} width={12} height={12}
                        rx={6} fill={colors.surface} />
                  <Rect x={scaleX(selected) - 4} y={scaleY(v) - 4} width={8} height={8}
                        rx={4} fill={c} />
                </React.Fragment>
              ))}
            </>
          )}
        </Svg>
      )}

      {/* Inspection box (outside the SVG, with text markers) */}
      <View style={{ minHeight: 20, alignItems: 'center' }}>
        {selected !== null ? (
          <RNText style={text.small}>
            {String(selected).padStart(2, '0')}:00 · Üretim{' '}
            <RNText style={{ color: colors.ink, fontWeight: '600' }}>
              {production[selected].toFixed(1)}
            </RNText>{' '}
            kWh · Tüketim{' '}
            <RNText style={{ color: colors.ink, fontWeight: '600' }}>
              {consumption[selected].toFixed(1)}
            </RNText>{' '}
            kWh
          </RNText>
        ) : (
          <RNText style={text.small}>Değerleri görmek için grafiğe dokun</RNText>
        )}
      </View>
    </View>
  );
}
