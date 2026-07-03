// Today screen: amber gradient hero (saving) + production/consumption chart +
// plan cards + proactive alerts. The plan comes from the deterministic endpoint.

import { LinearGradient } from 'expo-linear-gradient';
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator, Pressable, RefreshControl, ScrollView, Text, View,
} from 'react-native';
import { api, rangeTL } from '../api';
import DailyChart from '../components/DailyChart';
import { SunIcon, LeafIcon } from '../components/Icons';
import { ScreenHeader } from '../components/Brand';
import PlanCard from '../components/PlanCard';
import { spacing, font, card, colors, text } from '../theme';

function DaySelector({ day, setDay }) {
  return (
    <View style={{
      flexDirection: 'row', backgroundColor: colors.input, borderRadius: 20,
      borderWidth: 1, borderColor: colors.border, padding: 3,
    }}>
      {[['today', 'Bugün'], ['tomorrow', 'Yarın']].map(([value, label]) => (
        <Pressable
          key={value}
          onPress={() => setDay(value)}
          style={{
            paddingVertical: 6, paddingHorizontal: 16, borderRadius: 17,
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

export default function Today({ userId }) {
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
  }, [userId, day]);

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
        <View style={[card, { borderColor: colors.critical }]}>
          <Text style={[text.body, { color: colors.critical }]}>
            Sunucuya ulaşılamadı. Ayarlar sekmesinden API adresini kontrol et.
          </Text>
        </View>
      )}

      {loading && !plan && <ActivityIndicator style={{ marginTop: 48 }} color={colors.amber} />}

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
                Model: {plan.chart_data.models.production} · {plan.chart_data.models.consumption}
              </Text>
            )}
          </LinearGradient>

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
            <View style={card}>
              <Text style={text.body}>
                Planlanacak esnek cihaz yok. Ayarlar'dan çamaşır makinesi gibi cihazlar ekle —
                Voltaic onları en ucuz saate yerleştirsin.
              </Text>
            </View>
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
