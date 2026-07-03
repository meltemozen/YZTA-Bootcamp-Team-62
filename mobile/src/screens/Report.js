// Monthly report: realized saving + missed opportunity (counterfactual) + CO2.
// Figures are simulation-based and the screen states this honestly.

import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, Text, View } from 'react-native';
import { api, rangeTL } from '../api';
import { ScreenHeader } from '../components/Brand';
import { spacing, font, card, colors, text } from '../theme';

function Box({ label, value, subText, color }) {
  return (
    <View style={[card, { flex: 1, marginRight: spacing.s }]}>
      <Text style={text.label}>{label}</Text>
      <Text style={{
        fontFamily: font.title, fontSize: 24, letterSpacing: -0.3,
        color: color || colors.ink, marginTop: 6,
      }}>
        {value}
      </Text>
      {subText ? <Text style={[text.small, { marginTop: 4 }]}>{subText}</Text> : null}
    </View>
  );
}

export default function Report({ userId }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setReport(await api.report(userId));
    } catch {
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { load(); }, [load]);

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.page }}
      contentContainerStyle={{ padding: spacing.m, paddingTop: 56 }}
      refreshControl={
        <RefreshControl refreshing={loading} onRefresh={load} tintColor={colors.amber} />
      }
    >
      <ScreenHeader title="Ay Sonu Raporu" />

      {loading && !report && <ActivityIndicator style={{ marginTop: 48 }} color={colors.amber} />}

      {report && (
        <>
          <View style={{ flexDirection: 'row' }}>
            <Box
              label="Gerçekleşen"
              value={rangeTL(report.realized_saving_tl_min, report.realized_saving_tl_max)}
              subText={`${report.applied_count}/${report.total_count} öneri uygulandı`}
              color={colors.goodText}
            />
            <Box
              label="Kaçırılan fırsat"
              value={`${report.missed_saving_tl.toFixed(0)} TL`}
              subText="uygulanmayan öneriler"
              color={colors.amber}
            />
          </View>
          <View style={{ flexDirection: 'row' }}>
            <Box
              label="Önlenen karbon"
              value={`${report.co2_saved_kg.toFixed(1)} kg`}
              subText={`≈ ${report.car_km_equiv.toFixed(0)} km araba yolu`}
              color={colors.goodText}
            />
            <Box
              label="Ağaç eşdeğeri"
              value={`${report.tree_month_equiv.toFixed(1)} ağaç`}
              subText="bir aylık emilim gücü"
              color={colors.goodText}
            />
          </View>

          <View style={[card, { borderLeftWidth: 3, borderLeftColor: colors.amber }]}>
            <Text style={text.subtitle}>Voltaic'in yorumu · {report.month}</Text>
            <Text style={[text.body, { marginTop: spacing.s }]}>{report.note}</Text>
            <Text style={[text.small, { marginTop: spacing.s }]}>
              Çevresel etki, ETKB şebeke emisyon faktörüyle (0.44 kg CO₂e/kWh) hesaplanır.
              Güneşe kaydırdığın her kWh, şebekenin en yoğun saatlerindeki yükü de azaltır.
            </Text>
          </View>

          <Text style={[text.small, { textAlign: 'center', marginTop: spacing.s, lineHeight: 17 }]}>
            Tasarruf rakamları tarife + üretim tahminine dayalı simülasyondur;{'\n'}
            sayaç ölçümü değildir. Yöntem: docs/METHOD.md
          </Text>
        </>
      )}
    </ScrollView>
  );
}
