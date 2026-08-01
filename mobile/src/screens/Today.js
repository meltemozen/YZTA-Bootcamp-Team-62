// Today screen: amber gradient hero (saving) + production/consumption chart +
// plan cards + proactive alerts. The plan comes from the deterministic endpoint.

import { LinearGradient } from 'expo-linear-gradient';
import React, { useCallback, useEffect, useState } from 'react';
import {
  Pressable, RefreshControl, ScrollView, Text, View,
} from 'react-native';
import { api, rangeTL, WEATHER_SOURCE_NOTE } from '../api';
import DailyChart from '../components/DailyChart';
import { SunIcon, LeafIcon } from '../components/Icons';
import { ScreenHeader } from '../components/Brand';
import PlanCard from '../components/PlanCard';
import {
  DataQualityNotice, EmptyState, ErrorState, LoadingState,
} from '../components/States';
import { spacing, font, card, colors, text } from '../theme';

// "v1-lightgbm (2026-07-15)" — omits the date when a model has none (the
// hardcoded v0 physical/profile fallback has no training date).
// Raw artifact ids (v1-lightgbm …) are engineering detail; the user gets a
// plain-Turkish name. Unknown ids fall through unchanged rather than lying.
const MODEL_LABELS = {
  'v0-physical': 'fiziksel model',
  'v0-profile': 'profil tahmini',
  'v1-lightgbm': 'LightGBM v1',
  'v1-weather-regressor': 'hava tabanlı regresyon v1',
  'v1-generic-load-shape': 'yük şekli v1',
  'v2-catboost-calibrated': 'CatBoost kalibreli v2',
};
const modelLabel = (id) => MODEL_LABELS[id] || id;

function formatModel(version, trainedAt) {
  const label = modelLabel(version);
  return trainedAt ? `${label} (${trainedAt})` : label;
}

function DaySelector({ day, setDay }) {
  return (
    <View
      accessibilityRole="tablist"
      style={{
        flexDirection: 'row', backgroundColor: colors.input, borderRadius: 20,
        borderWidth: 1, borderColor: colors.border, padding: 3,
      }}
    >
      {[['today', 'Bugün'], ['tomorrow', 'Yarın']].map(([value, label]) => (
        <Pressable
          key={value}
          onPress={() => setDay(value)}
          accessibilityRole="tab"
          accessibilityState={{ selected: day === value }}
          accessibilityLabel={`${label} planı`}
          style={{
            paddingVertical: 9, paddingHorizontal: 16, borderRadius: 17,
            backgroundColor: day === value ? colors.amber : 'transparent',
          }}
        >
          <Text style={{
            fontSize: 12.5, fontFamily: font.semibold,
            color: day === value ? colors.amberInk : colors.inkSecondary,
          }}>
            {label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

export default function Today({ userId, refreshKey = 0 }) {
  const [day, setDay] = useState('today');
  const [plan, setPlan] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, n] = await Promise.all([
        api.plan(userId, day),
        api.notifications(userId).catch(() => ({ notifications: [] })),
      ]);
      setPlan(p);
      setAlerts(n.notifications);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [userId, day, refreshKey]);

  useEffect(() => { load(); }, [load]);

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.page }}
      contentContainerStyle={{ padding: spacing.m, paddingTop: 56, paddingBottom: 32 }}
      refreshControl={
        <RefreshControl refreshing={loading} onRefresh={load} tintColor={colors.amber} />
      }
    >
      <ScreenHeader title="Enerji Planın" right={<DaySelector day={day} setDay={setDay} />} />

      {error && (
        <ErrorState
          message={plan
            ? 'Plan yenilenemedi, aşağıdakiler en son alınan veriler.'
            : 'Sunucudan plan alınamadı.'}
          hint={`Ayarlar sekmesinden sunucu adresini kontrol edebilirsin. (${error})`}
          onRetry={load}
        />
      )}

      {loading && !plan && <LoadingState variant="plan" label="Planın hazırlanıyor…" />}

      {plan && (
        <>
          {/* Hero: gradient saving card */}
          <LinearGradient
            colors={[colors.amber, colors.amberDark]}
            start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
            style={{ borderRadius: 18, padding: spacing.l, marginBottom: spacing.m }}
          >
            <Text style={{
              fontFamily: font.semibold, fontSize: 11, letterSpacing: 1.2,
              textTransform: 'uppercase', color: 'rgba(34,21,0,0.65)',
            }}>
              Bu planla tahmini tasarruf
            </Text>
            <Text style={{
              fontFamily: font.title, fontSize: 40, color: colors.amberInk,
              letterSpacing: -0.5, marginTop: 2,
            }}>
              {rangeTL(plan.total_saving_tl_min, plan.total_saving_tl_max)}
            </Text>
            <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 8, gap: 6 }}>
              <LeafIcon size={15} color="rgba(34,21,0,0.75)" />
              <Text style={{ fontFamily: font.medium, fontSize: 13, color: 'rgba(34,21,0,0.75)' }}>
                {plan.co2_saved_kg.toFixed(1)} kg CO₂
                {plan.chart_data.env?.car_km
                  ? ` ≈ ${plan.chart_data.env.car_km.toFixed(0)} km araba yolu`
                  : ''} · öz tüketim %{Math.round(plan.self_consumption_ratio * 100)}
              </Text>
            </View>
            <Text style={{
              fontFamily: font.body, fontSize: 11.5, color: 'rgba(34,21,0,0.6)', marginTop: 8,
            }}>
              Aralık gösteriyoruz: tüketimin faturadan tahmin ediliyor — dürüst rakam.
            </Text>
            {plan.chart_data.models && (
              <Text style={{
                fontFamily: font.body, fontSize: 10.5, color: 'rgba(34,21,0,0.55)', marginTop: 5,
              }}>
                Üretim: {formatModel(plan.chart_data.models.production, plan.chart_data.models.production_trained_at)}
                {' · '}Tüketim:{' '}
                {formatModel(plan.chart_data.models.consumption, plan.chart_data.models.consumption_trained_at)}
                {plan.chart_data.models.optimizer ? ` · Optimizer: ${plan.chart_data.models.optimizer}` : ''}
              </Text>
            )}
            {plan.weather_source && (
              <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 6, gap: 6 }}>
                <View style={{
                  paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8,
                  backgroundColor: plan.weather_source === 'live' ? 'rgba(47,191,102,0.25)'
                    : plan.weather_source === 'cached' ? 'rgba(247,179,43,0.25)'
                    : 'rgba(242,109,109,0.25)',
                }}>
                  <Text style={{
                    fontFamily: font.semibold, fontSize: 9.5, letterSpacing: 0.5,
                    textTransform: 'uppercase',
                    color: plan.weather_source === 'live' ? '#1a6b35'
                      : plan.weather_source === 'cached' ? '#6b4400'
                      : '#6b1a1a',
                  }}>
                    Hava: {plan.weather_source === 'live' ? 'Canlı'
                      : plan.weather_source === 'cached' ? 'Önbellek'
                      : 'Sentetik'}
                  </Text>
                </View>
              </View>
            )}
          </LinearGradient>

          <DataQualityNotice weatherSource={plan.chart_data.data_quality?.weather_source} />

          {/* Chart */}
          <View style={card}>
            <Text style={[text.label, { marginBottom: spacing.s }]}>24 saatlik görünüm</Text>
            <DailyChart
              production={plan.chart_data.production}
              consumption={plan.chart_data.consumption}
              band={plan.chart_data.band}
            />
          </View>

          {/* Plan items */}
          {plan.items.length > 0 && (
            <Text style={[text.label, { marginBottom: spacing.s, marginLeft: 2 }]}>
              Günün planı
            </Text>
          )}
          {plan.items.length === 0 ? (
            <EmptyState
              title="Bugün kaydırılacak bir şey yok"
              message={'Zamanı esnek bir cihazın kayıtlı değil. Çamaşır makinesi, bulaşık '
                + 'makinesi veya EV şarjı eklersen Wattra bunları en ucuz saate yerleştirir.'}
            />
          ) : (
            plan.items.map((item, i) => (
              <PlanCard key={i} item={item} userId={userId} date={plan.date} />
            ))
          )}

          {/* Proactive alerts */}
          {alerts.map((alert, i) => (
            <View
              key={i}
              style={[card, {
                flexDirection: 'row', gap: 12,
                borderLeftWidth: 3, borderLeftColor: colors.amber,
              }]}
            >
              <View style={{
                width: 38, height: 38, borderRadius: 19, backgroundColor: colors.amberSoft,
                alignItems: 'center', justifyContent: 'center',
              }}>
                <SunIcon size={20} color={colors.amber} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={text.subtitle}>{alert.title.replace(' ☀️', '')}</Text>
                <Text style={[text.body, { marginTop: 3, fontSize: 13.5 }]}>{alert.text}</Text>
              </View>
            </View>
          ))}
        </>
      )}
    </ScrollView>
  );
}
