// Today screen: amber gradient hero (saving) + production/consumption chart +
// plan cards + proactive alerts. The plan comes from the deterministic endpoint.

import { LinearGradient } from 'expo-linear-gradient';
import React, { useCallback, useEffect, useState } from 'react';
import {
  Pressable, RefreshControl, ScrollView, Text, View,
} from 'react-native';
import { api, rangeTL } from '../api';
import DailyChart from '../components/DailyChart';
import { DeviceRunningToggle } from '../components/DeviceControls';
import { SunIcon, LeafIcon } from '../components/Icons';
import { ScreenHeader } from '../components/Brand';
import PlanCard from '../components/PlanCard';
import {
  EmptyState, ErrorState, InlineNotice, LoadingState,
} from '../components/States';
import { spacing, font, card, colors, text } from '../theme';

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
  const [profile, setProfile] = useState(null);
  const [deviceStatusBusy, setDeviceStatusBusy] = useState('');
  const [deviceStatus, setDeviceStatus] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, n, userProfile] = await Promise.all([
        api.plan(userId, day),
        api.notifications(userId).catch(() => ({ notifications: [] })),
        api.profile(userId).catch(() => null),
      ]);
      setPlan(p);
      setAlerts(n.notifications);
      if (userProfile) setProfile(userProfile);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [userId, day, refreshKey]);

  useEffect(() => { load(); }, [load]);

  const updateRunningState = async (deviceName, patch) => {
    if (!profile) return;
    const previous = profile;
    const next = {
      ...profile,
      devices: profile.devices.map((device) =>
        device.name === deviceName ? { ...device, ...patch } : device),
    };
    setProfile(next);
    setDeviceStatusBusy(deviceName);
    setDeviceStatus(null);
    try {
      await api.updateProfile(userId, next);
      setDeviceStatus({
        tone: 'success',
        message: patch.is_running
          ? `${deviceName} çalışıyor olarak işaretlendi.`
          : `${deviceName} kapalı olarak işaretlendi.`,
      });
      setPlan(await api.plan(userId, day));
    } catch {
      setProfile(previous);
      setDeviceStatus({
        tone: 'error',
        message: 'Cihaz durumu kaydedilemedi. Bağlantını kontrol edip yeniden dene.',
      });
    } finally {
      setDeviceStatusBusy('');
    }
  };

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
            : 'Plan şu anda alınamadı.'}
          hint="Bağlantını kontrol edip tekrar dene."
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
            <View style={{ flexDirection: 'row', marginTop: 12, gap: 18 }}>
              <View>
                <Text style={{ fontFamily: font.body, fontSize: 10.5, color: 'rgba(34,21,0,0.6)' }}>
                  Beklenen üretim
                </Text>
                <Text style={{ fontFamily: font.semibold, fontSize: 14, color: colors.amberInk }}>
                  {plan.chart_data.production.reduce((sum, value) => sum + value, 0).toFixed(1)} kWh
                </Text>
              </View>
              <View>
                <Text style={{ fontFamily: font.body, fontSize: 10.5, color: 'rgba(34,21,0,0.6)' }}>
                  Beklenen tüketim
                </Text>
                <Text style={{ fontFamily: font.semibold, fontSize: 14, color: colors.amberInk }}>
                  {plan.chart_data.consumption.reduce((sum, value) => sum + value, 0).toFixed(1)} kWh
                </Text>
              </View>
            </View>
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

          {profile?.devices?.length > 0 ? (
            <View style={card}>
              <Text style={[text.label, { marginBottom: spacing.s }]}>Cihaz durumu</Text>
              <Text style={[text.small, { marginBottom: spacing.s, lineHeight: 17 }]}>
                Çalışan cihazı işaretlediğinde bugünkü tüketim ve plan hemen güncellenir.
              </Text>
              {profile.devices.map((device, index) => (
                <View
                  key={device.name}
                  style={{
                    paddingVertical: spacing.s,
                    borderTopWidth: index === 0 ? 0 : 1,
                    borderTopColor: colors.line,
                  }}
                >
                  <Text style={text.subtitle}>{device.name}</Text>
                  <DeviceRunningToggle
                    device={device}
                    disabled={Boolean(deviceStatusBusy)}
                    onChange={(patch) => updateRunningState(device.name, patch)}
                  />
                </View>
              ))}
              <InlineNotice
                tone={deviceStatus?.tone}
                message={deviceStatus?.message}
              />
            </View>
          ) : null}

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
