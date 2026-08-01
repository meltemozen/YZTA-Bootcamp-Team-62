// Post-onboarding editors: the user's own tariff prices and their device list.
// Both write the whole HouseholdProfile back through PUT /api/profile, so the
// parent owns the profile state and passes a save function down.

import React, { useState } from 'react';
import { ActivityIndicator, Pressable, Text, TextInput, View } from 'react-native';
import { TOUCH } from './States';
import { spacing, font, card, colors, text } from '../theme';

function Field({ label, value, onChange, placeholder, error }) {
  return (
    <View style={{ flex: 1, minWidth: 96 }}>
      <Text style={[text.small, { marginBottom: 4 }]}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={colors.faint}
        keyboardType="numeric"
        accessibilityLabel={label}
        style={{
          borderWidth: 1, borderColor: error ? colors.critical : colors.border,
          borderRadius: 10, paddingHorizontal: 10, minHeight: TOUCH,
          backgroundColor: colors.input, color: colors.ink,
          fontFamily: font.number, fontSize: 15,
        }}
      />
    </View>
  );
}

function ActionButton({ label, onPress, tone = 'default', busy, disabled }) {
  const isPrimary = tone === 'primary';
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || busy}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !!(disabled || busy) }}
      style={{
        minHeight: TOUCH, borderRadius: 12, paddingHorizontal: 18,
        alignItems: 'center', justifyContent: 'center',
        backgroundColor: isPrimary ? colors.amber : 'transparent',
        borderWidth: isPrimary ? 0 : 1,
        borderColor: tone === 'danger' ? colors.critical : colors.border,
        opacity: disabled || busy ? 0.45 : 1,
      }}
    >
      {busy ? <ActivityIndicator color={isPrimary ? colors.amberInk : colors.amber} /> : (
        <Text style={{
          fontFamily: font.semibold, fontSize: 14,
          color: isPrimary ? colors.amberInk
            : tone === 'danger' ? colors.critical : colors.ink,
        }}>
          {label}
        </Text>
      )}
    </Pressable>
  );
}

const num = (s) => {
  const v = parseFloat(String(s).replace(',', '.'));
  return Number.isFinite(v) && v > 0 ? v : null;
};

/** Lets the user replace our built-in EPDK snapshot with the prices on their
 *  own bill. Empty fields keep the regulated value, so partial entry is fine. */
export function TariffEditor({ profile, onSave }) {
  const existing = profile.custom_tariff || {};
  const [single, setSingle] = useState(existing.single ? String(existing.single) : '');
  const [day, setDay] = useState(existing.day ? String(existing.day) : '');
  const [peak, setPeak] = useState(existing.peak ? String(existing.peak) : '');
  const [night, setNight] = useState(existing.night ? String(existing.night) : '');
  const [sell, setSell] = useState(existing.sell ? String(existing.sell) : '');
  const [busy, setBusy] = useState(false);

  const threeZone = profile.tariff_type === 'three_zone';

  const save = async (clear) => {
    setBusy(true);
    try {
      const custom = clear ? null : {
        single: threeZone ? null : num(single),
        day: threeZone ? num(day) : null,
        peak: threeZone ? num(peak) : null,
        night: threeZone ? num(night) : null,
        sell: num(sell),
      };
      const empty = !custom || Object.values(custom).every((v) => v === null);
      await onSave({ ...profile, custom_tariff: empty ? null : custom });
      if (clear) { setSingle(''); setDay(''); setPeak(''); setNight(''); setSell(''); }
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={card}>
      <Text style={text.label}>Kendi tarifem</Text>
      <Text style={[text.small, { marginTop: spacing.s, lineHeight: 17 }]}>
        Uygulamadaki fiyatlar EPDK'nın 4 Nisan 2026 tablosundan gelir. Faturandaki
        birim fiyat farklıysa buraya yaz — tasarruf hesabı senin fiyatınla yapılır.
        Boş bıraktığın alanlar varsayılan tarifeden devam eder.
      </Text>

      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.s,
                     marginTop: spacing.m }}>
        {threeZone ? (
          <>
            <Field label="Gündüz 06-17" value={day} onChange={setDay} placeholder="5.57" />
            <Field label="Puant 17-22" value={peak} onChange={setPeak} placeholder="7.85" />
            <Field label="Gece 22-06" value={night} onChange={setNight} placeholder="3.74" />
          </>
        ) : (
          <Field label="Birim fiyat" value={single} onChange={setSingle} placeholder="4.86" />
        )}
        <Field label="Satış (mahsup)" value={sell} onChange={setSell} placeholder="otomatik" />
      </View>
      <Text style={[text.small, { marginTop: 6 }]}>
        TL/kWh, vergiler dahil. Satış fiyatını bilmiyorsan boş bırak — alış
        fiyatının ~%70'i olarak hesaplanır.
      </Text>

      <View style={{ flexDirection: 'row', gap: spacing.s, marginTop: spacing.m }}>
        <View style={{ flex: 1 }}>
          <ActionButton label="Fiyatlarımı kaydet" tone="primary" busy={busy}
                        onPress={() => save(false)} />
        </View>
        {profile.custom_tariff ? (
          <ActionButton label="Varsayılana dön" onPress={() => save(true)} disabled={busy} />
        ) : null}
      </View>
    </View>
  );
}

/** Add/remove flexible devices and correct the assumed kWh / duration / power.
 *  These three numbers drive the optimizer directly, so a wrong catalog
 *  assumption (e.g. a 7 kW EV charger on a 3 kW supply) is worth fixing. */
export function DeviceEditor({ profile, catalog, onSave }) {
  const [devices, setDevices] = useState(profile.devices || []);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);

  const update = (index, patch) => {
    setDevices((current) =>
      current.map((d, i) => (i === index ? { ...d, ...patch } : d)));
    setDirty(true);
  };

  const remove = (index) => {
    setDevices((current) => current.filter((_, i) => i !== index));
    setDirty(true);
  };

  const add = (device) => {
    setDevices((current) => [...current, device]);
    setDirty(true);
  };

  const save = async () => {
    setBusy(true);
    try {
      // Empty/invalid numbers fall back to the value we started from rather
      // than silently becoming 0 — a 0 kWh device would vanish from the plan.
      const cleaned = devices.map((d) => ({
        ...d,
        kwh: num(d.kwh) ?? 1,
        duration_h: Math.min(12, Math.max(1, Math.round(num(d.duration_h) ?? 1))),
        power_kw: num(d.power_kw),
      }));
      await onSave({ ...profile, devices: cleaned });
      setDevices(cleaned);
      setDirty(false);
    } finally {
      setBusy(false);
    }
  };

  const owned = new Set(devices.map((d) => d.name));
  const addable = (catalog || []).filter((c) => !owned.has(c.name));

  return (
    <View style={card}>
      <Text style={text.label}>Cihazlarım</Text>
      <Text style={[text.small, { marginTop: spacing.s, lineHeight: 17 }]}>
        Bu değerler planı doğrudan belirler. Cihazının etiketindeki gerçek
        tüketim/güç farklıysa düzelt — plan da ona göre kurulur.
      </Text>

      {devices.length === 0 ? (
        <Text style={[text.body, { marginTop: spacing.m }]}>
          Kayıtlı cihazın yok. Aşağıdan ekleyebilirsin.
        </Text>
      ) : devices.map((device, index) => (
        <View key={`${device.name}-${index}`}
              style={{
                marginTop: spacing.m, paddingTop: spacing.m,
                borderTopWidth: 1, borderTopColor: colors.line,
              }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.s }}>
            <Text style={[text.subtitle, { flex: 1 }]}>{device.name}</Text>
            <ActionButton label="Çıkar" tone="danger" onPress={() => remove(index)} />
          </View>
          <View style={{ flexDirection: 'row', gap: spacing.s, marginTop: spacing.s }}>
            <Field label="kWh / çalışma" value={String(device.kwh ?? '')}
                   onChange={(v) => update(index, { kwh: v })} />
            <Field label="Süre (saat)" value={String(device.duration_h ?? '')}
                   onChange={(v) => update(index, { duration_h: v })} />
            <Field label="Güç (kW)" value={device.power_kw == null ? '' : String(device.power_kw)}
                   onChange={(v) => update(index, { power_kw: v })} placeholder="bilinmiyor" />
          </View>
        </View>
      ))}

      {addable.length > 0 && (
        <View style={{ marginTop: spacing.m, paddingTop: spacing.m,
                       borderTopWidth: 1, borderTopColor: colors.line }}>
          <Text style={[text.small, { marginBottom: spacing.s }]}>Cihaz ekle</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.s }}>
            {addable.map((device) => (
              <Pressable
                key={device.name}
                onPress={() => add(device)}
                accessibilityRole="button"
                accessibilityLabel={`${device.name} ekle`}
                style={{
                  borderWidth: 1, borderColor: colors.border, borderRadius: 12,
                  paddingHorizontal: 13, minHeight: TOUCH, justifyContent: 'center',
                  backgroundColor: colors.input,
                }}
              >
                <Text style={[text.small, { color: colors.inkSecondary }]}>
                  + {device.name}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>
      )}

      {dirty && (
        <View style={{ marginTop: spacing.m }}>
          <ActionButton label="Cihazlarımı kaydet" tone="primary" busy={busy} onPress={save} />
        </View>
      )}
    </View>
  );
}
