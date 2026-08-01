// Monthly report: estimated saving (simulation-based) + missed opportunity
// (counterfactual) + CO2. Figures are simulation-based and the screen states
// this honestly.

import React, { useCallback, useEffect, useState } from 'react';
import { RefreshControl, ScrollView, Text, View } from 'react-native';
import { api, rangeTL } from '../api';
import { ScreenHeader } from '../components/Brand';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
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

export default function Report({ userId, refreshKey = 0 }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setReport(await api.report(userId));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [userId, refreshKey]);

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

      {loading && !report && <LoadingState label="Rapor hesaplanıyor…" />}

      {error && !report && (
        <ErrorState
          message="Ay sonu raporu alınamadı."
          hint={`Ayarlar sekmesinden sunucu adresini kontrol edebilirsin. (${error})`}
          onRetry={load}
        />
      )}

      {report && report.total_count === 0 && (
        <EmptyState
          title="Henüz raporlanacak bir ay yok"
          message={'Bu ay için kaydedilmiş bir plan bulunmuyor. Bugün sekmesinden planını '
            + 'oluştur ve uyguladığın önerileri işaretle — ay sonunda gerçekleşen tasarrufunu '
            + 've kaçırdığın fırsatı burada göreceksin.'}
        />
      )}

      {report && report.total_count > 0 && (
        <>
          <View style={{ flexDirection: 'row' }}>
            <Box
              label="Uygulanan (tahmini)"
              value={rangeTL(report.realized_saving_tl_min, report.realized_saving_tl_max)}
              subText={`${report.applied_count}/${report.total_count} öneri uygulandı (simülasyon)`}
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
            <Text style={text.subtitle}>Wattra'in yorumu · {report.month}</Text>
            <Text style={[text.body, { marginTop: spacing.s }]}>{report.note}</Text>
            <Text style={[text.small, { marginTop: spacing.s }]}>
              Çevresel etki, ETKB şebeke emisyon faktörüyle (0.44 kg CO₂e/kWh) hesaplanır.
              Güneşe kaydırdığın her kWh, şebekenin en yoğun saatlerindeki yükü de azaltır.
            </Text>
          </View>

          <Text style={[text.small, { textAlign: 'center', marginTop: spacing.s, lineHeight: 17 }]}>
            {report.data_disclaimer || 'Tasarruf rakamları tarife + üretim tahminine dayalı simülasyondur.'}
            {'\n'}Sayaç ölçümü değildir. Yöntem: docs/METHOD.md
          </Text>
        </>
      )}
    </ScrollView>
  );
}
