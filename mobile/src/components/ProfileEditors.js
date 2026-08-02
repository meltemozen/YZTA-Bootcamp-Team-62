// Post-onboarding editors: the user's own tariff prices and their device list.
// Both write the whole HouseholdProfile back through PUT /api/profile, so the
// parent owns the profile state and passes a save function down.

import React, { useState } from 'react';
import { ActivityIndicator, Pressable, Text, TextInput, View } from 'react-native';
import {
  DeviceStatusControls, FlexibilityToggle, ManualDeviceForm,
} from './DeviceControls';
import LocationPicker from './LocationPicker';
import { InlineNotice, TOUCH } from './States';
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

const nonNegative = (s) => {
  const value = parseFloat(String(s).replace(',', '.'));
  return Number.isFinite(value) && value >= 0 ? value : null;
};

export function LocationEditor({ profile, onSave }) {
  const savedLocation = { name: profile.city, lat: profile.lat, lon: profile.lon };
  const [editing, setEditing] = useState(false);
  const [location, setLocation] = useState(savedLocation);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const save = async () => {
    if (!location?.name || !Number.isFinite(location.lat) || !Number.isFinite(location.lon)) {
      setError('Kaydetmeden önce sistem konumunu belirle.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const saved = await onSave({
        ...profile,
        city: location.name,
        lat: location.lat,
        lon: location.lon,
      });
      if (saved === false) {
        setError('Konum kaydedilemedi. Bağlantını kontrol edip yeniden dene.');
        return;
      }
      setEditing(false);
    } finally {
      setBusy(false);
    }
  };

  const cancel = () => {
    setLocation(savedLocation);
    setError('');
    setEditing(false);
  };

  return (
    <View style={card}>
      <Text style={text.label}>Sabit sistem konumu</Text>
      {!editing ? (
        <>
          <Text style={[text.body, { color: colors.ink, marginTop: spacing.s }]}>
            {profile.city}
          </Text>
          <Text style={[text.small, { marginTop: 5, lineHeight: 18 }]}>
            Hava durumu ve üretim tahminleri bu kayıtlı konumdan hesaplanır.
            Uygulama her açılışta GPS kullanmaz.
          </Text>
          <View style={{ marginTop: spacing.m }}>
            <ActionButton label="Konumu değiştir" onPress={() => setEditing(true)} />
          </View>
        </>
      ) : (
        <View style={{ marginTop: spacing.m }}>
          <LocationPicker
            value={location}
            onChange={setLocation}
            placeLabel={profile.user_type === 'business' ? 'İşyerinin' : 'Evinin'}
          />
          <InlineNotice tone="error" message={error} />
          <View style={{ flexDirection: 'row', gap: spacing.s }}>
            <View style={{ flex: 1 }}>
              <ActionButton
                label="Yeni konumu kaydet"
                tone="primary"
                busy={busy}
                onPress={save}
              />
            </View>
            <ActionButton label="Vazgeç" disabled={busy} onPress={cancel} />
          </View>
        </View>
      )}
    </View>
  );
}

export function SystemEditor({ profile, onSave }) {
  const [panel, setPanel] = useState(String(profile.panel_kw));
  const [battery, setBattery] = useState(String(profile.battery_kwh));
  const [batteryPower, setBatteryPower] = useState(String(profile.battery_power_kw));
  const [monthly, setMonthly] = useState(String(profile.monthly_bill_kwh));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const save = async () => {
    const panelValue = num(panel);
    const batteryValue = nonNegative(battery);
    const powerValue = nonNegative(batteryPower);
    const monthlyValue = num(monthly);
    if (panelValue === null || batteryValue === null || powerValue === null || monthlyValue === null) {
      setError('Sistem değerlerini sıfır veya daha büyük geçerli sayılarla doldur.');
      return;
    }
    if (batteryValue === 0 && powerValue > 0) {
      setError('Batarya kapasitesi 0 ise batarya gücü de 0 olmalı.');
      return;
    }
    setError('');
    setBusy(true);
    try {
      await onSave({
        ...profile,
        panel_kw: panelValue,
        battery_kwh: batteryValue,
        battery_power_kw: powerValue,
        monthly_bill_kwh: monthlyValue,
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={card}>
      <Text style={text.label}>Enerji sistemim</Text>
      <Text style={[text.small, { marginTop: spacing.s, lineHeight: 17 }]}>
        Panel, batarya ve son faturandaki tüketim değerlerini güncel tut.
      </Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.s, marginTop: spacing.m }}>
        <Field label="Panel gücü (kW)" value={panel} onChange={setPanel} />
        <Field label="Batarya (kWh)" value={battery} onChange={setBattery} />
        <Field label="Batarya gücü (kW)" value={batteryPower} onChange={setBatteryPower} />
        <Field label="Aylık tüketim (kWh)" value={monthly} onChange={setMonthly} />
      </View>
      {error ? <Text style={[text.small, { color: colors.critical, marginTop: spacing.s }]}>{error}</Text> : null}
      <View style={{ marginTop: spacing.m }}>
        <ActionButton label="Sistem bilgilerimi kaydet" tone="primary" busy={busy} onPress={save} />
      </View>
    </View>
  );
}

/** Lets the user keep the optimizer aligned with the prices on their bill. */
export function TariffEditor({ profile, onSave }) {
  const existing = profile.custom_tariff || {};
  const [single, setSingle] = useState(existing.single ? String(existing.single) : '');
  const [day, setDay] = useState(existing.day ? String(existing.day) : '');
  const [peak, setPeak] = useState(existing.peak ? String(existing.peak) : '');
  const [night, setNight] = useState(existing.night ? String(existing.night) : '');
  const [sell, setSell] = useState(existing.sell != null ? String(existing.sell) : '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const threeZone = profile.tariff_type === 'three_zone';

  const save = async () => {
    const sellValue = String(sell).trim() === '0' ? 0 : num(sell);
    const required = threeZone ? [num(day), num(peak), num(night)] : [num(single)];
    if (required.some((value) => value === null) || sellValue === null) {
      setError('Faturandaki geçerli birim fiyatları eksiksiz gir.');
      return;
    }
    setError('');
    setBusy(true);
    try {
      const custom = {
        single: threeZone ? null : num(single),
        day: threeZone ? num(day) : null,
        peak: threeZone ? num(peak) : null,
        night: threeZone ? num(night) : null,
        sell: sellValue,
      };
      await onSave({ ...profile, custom_tariff: custom });
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={card}>
      <Text style={text.label}>Kendi tarifem</Text>
      <Text style={[text.small, { marginTop: spacing.s, lineHeight: 17 }]}>
        Faturandaki vergiler dahil birim fiyatları gir. Planın maliyet hesabı doğrudan
        bu değerlerle güncellenir.
      </Text>

      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.s,
                     marginTop: spacing.m }}>
        {threeZone ? (
          <>
            <Field label="Gündüz 06-17" value={day} onChange={setDay} placeholder="TL/kWh" />
            <Field label="Puant 17-22" value={peak} onChange={setPeak} placeholder="TL/kWh" />
            <Field label="Gece 22-06" value={night} onChange={setNight} placeholder="TL/kWh" />
          </>
        ) : (
          <Field label="Birim fiyat" value={single} onChange={setSingle} placeholder="TL/kWh" />
        )}
        <Field label="Satış (mahsup)" value={sell} onChange={setSell} placeholder="0" />
      </View>
      <Text style={[text.small, { marginTop: 6 }]}>
        Şebekeye satış bedelini faturandaki veya sözleşmendeki değerden gir. Satış
        anlaşman yoksa 0 yaz.
      </Text>
      {error ? <Text style={[text.small, { marginTop: 6, color: colors.critical }]}>{error}</Text> : null}

      <View style={{ flexDirection: 'row', gap: spacing.s, marginTop: spacing.m }}>
        <View style={{ flex: 1 }}>
          <ActionButton label="Fiyatlarımı kaydet" tone="primary" busy={busy}
                        onPress={save} />
        </View>
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
  const [error, setError] = useState('');
  const [showManual, setShowManual] = useState(false);
  const [statusBusy, setStatusBusy] = useState('');
  const [statusNotice, setStatusNotice] = useState('');

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
    setDevices((current) => [...current, {
      ...device,
      enabled: device.enabled !== false,
      is_running: !!device.is_running,
      status_updated_at: device.status_updated_at || null,
      user_defined: !!device.user_defined,
    }]);
    setDirty(true);
  };

  const persistStatus = async (index, patch) => {
    const device = devices[index];
    const previous = devices;
    const next = devices.map((item, itemIndex) =>
      itemIndex === index ? { ...item, ...patch } : item);
    setDevices(next);
    setStatusNotice('');

    const savedDevice = (profile.devices || []).find((item) => item.name === device.name);
    if (!savedDevice) {
      setDirty(true);
      return;
    }

    setStatusBusy(device.name);
    const persisted = profile.devices.map((item) =>
      item.name === device.name ? { ...item, ...patch } : item);
    const saved = await onSave({ ...profile, devices: persisted }, { silent: true });
    if (saved === false) {
      setDevices(previous);
      setError('Cihaz durumu kaydedilemedi. Bağlantını kontrol edip yeniden dene.');
    } else {
      setStatusNotice(
        patch.is_running === true ? `${device.name} çalışıyor olarak işaretlendi.`
          : patch.is_running === false ? `${device.name} kapalı olarak işaretlendi.`
            : `${device.name} planlama ayarı güncellendi.`
      );
    }
    setStatusBusy('');
  };

  const save = async () => {
    const invalid = devices.some((device) => {
      const duration = num(device.duration_h);
      const hasPower = String(device.power_kw ?? '').trim() !== '';
      const earliest = Number(device.earliest);
      const latest = Number(device.latest);
      return num(device.kwh) === null || duration === null || duration > 12
        || (hasPower && num(device.power_kw) === null)
        || !Number.isInteger(earliest) || !Number.isInteger(latest)
        || earliest < 0 || latest > 23 || earliest > latest
        || earliest + Math.ceil(duration) - 1 > latest;
    });
    if (invalid) {
      setError('Tüketim ve süre alanlarını cihaz etiketindeki geçerli değerlerle doldur.');
      return;
    }
    setError('');
    setBusy(true);
    try {
      const cleaned = devices.map((d) => ({
        ...d,
        kwh: num(d.kwh),
        duration_h: Math.round(num(d.duration_h)),
        power_kw: String(d.power_kw ?? '').trim() === '' ? null : num(d.power_kw),
        earliest: Number(d.earliest),
        latest: Number(d.latest),
        enabled: d.enabled !== false,
        is_running: !!d.is_running,
        status_updated_at: d.status_updated_at || null,
        user_defined: !!d.user_defined,
      }));
      const saved = await onSave({ ...profile, devices: cleaned });
      if (saved === false) {
        setError('Cihazlar kaydedilemedi. Bağlantını kontrol edip yeniden dene.');
        return;
      }
      setDevices(cleaned);
      setDirty(false);
    } finally {
      setBusy(false);
    }
  };

  const owned = new Set(devices.map((d) => d.name));
  const addable = (catalog || []).filter((device) =>
    !owned.has(device.name)
    && (profile.user_type === 'business' || !device.name.includes('işyeri')));

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
          <DeviceStatusControls
            device={device}
            disabled={Boolean(statusBusy)}
            onChange={(patch) => persistStatus(index, patch)}
          />
          <View style={{
            flexDirection: 'row', flexWrap: 'wrap', gap: spacing.s, marginTop: spacing.s,
          }}>
            <Field label="kWh / çalışma" value={String(device.kwh ?? '')}
                   onChange={(v) => update(index, { kwh: v })} />
            <Field label="Süre (saat)" value={String(device.duration_h ?? '')}
                   onChange={(v) => update(index, { duration_h: v })} />
            <Field label="Güç (kW)" value={device.power_kw == null ? '' : String(device.power_kw)}
                   onChange={(v) => update(index, { power_kw: v })} placeholder="bilinmiyor" />
            <Field label="En erken" value={String(device.earliest ?? 0)}
                   onChange={(v) => update(index, { earliest: v })} />
            <Field label="En geç bitiş" value={String(device.latest ?? 23)}
                   onChange={(v) => update(index, { latest: v })} />
          </View>
          <View style={{ marginTop: spacing.s }}>
            <FlexibilityToggle
              value={device.flexibility || 'shiftable'}
              onChange={(flexibility) => update(index, { flexibility })}
            />
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

      <View style={{ marginTop: spacing.m }}>
        <ActionButton label="Kendi cihazımı ekle" onPress={() => setShowManual(true)} />
      </View>
      {showManual ? (
        <ManualDeviceForm
          existingNames={devices.map((device) => device.name)}
          onCancel={() => setShowManual(false)}
          onAdd={(device) => {
            add(device);
            setShowManual(false);
          }}
        />
      ) : null}

      <InlineNotice tone="success" message={statusNotice} />

      {dirty && (
        <View style={{ marginTop: spacing.m }}>
          {error ? (
            <Text style={[text.small, { color: colors.critical, marginBottom: spacing.s }]}>
              {error}
            </Text>
          ) : null}
          <ActionButton label="Cihazlarımı kaydet" tone="primary" busy={busy} onPress={save} />
        </View>
      )}
    </View>
  );
}
