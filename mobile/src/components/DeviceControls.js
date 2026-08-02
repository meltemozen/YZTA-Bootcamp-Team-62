import React, { useState } from 'react';
import {
  Pressable, Switch, Text, TextInput, View,
} from 'react-native';
import { InlineNotice, TOUCH } from './States';
import {
  colors, font, inputField, primaryButton, primaryButtonText, spacing, text,
} from '../theme';

function NumericField({ label, value, onChange, unit }) {
  return (
    <View style={{ flex: 1, minWidth: 110 }}>
      <Text style={[text.small, { marginBottom: 4 }]}>{label}</Text>
      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
        <TextInput
          value={value}
          onChangeText={onChange}
          keyboardType="numeric"
          accessibilityLabel={label}
          style={[inputField, { flex: 1, minHeight: TOUCH, padding: 11 }]}
        />
        {unit ? <Text style={[text.small, { marginLeft: 5 }]}>{unit}</Text> : null}
      </View>
    </View>
  );
}

function ToggleRow({ label, detail, value, onValueChange, disabled }) {
  return (
    <View style={{
      minHeight: TOUCH, flexDirection: 'row', alignItems: 'center',
      justifyContent: 'space-between', gap: spacing.m,
    }}>
      <View style={{ flex: 1 }}>
        <Text style={[text.body, { color: colors.ink }]}>{label}</Text>
        {detail ? <Text style={[text.small, { marginTop: 2 }]}>{detail}</Text> : null}
      </View>
      <Switch
        value={value}
        onValueChange={onValueChange}
        disabled={disabled}
        accessibilityLabel={label}
        trackColor={{ false: colors.raised, true: colors.amber }}
        thumbColor={value ? colors.amberInk : colors.inkSecondary}
      />
    </View>
  );
}

export function isDeviceRunningNow(device) {
  if (!device?.is_running) return false;
  if (!device.status_updated_at) return true;
  const started = new Date(device.status_updated_at).getTime();
  if (!Number.isFinite(started)) return true;
  const durationMs = Math.max(Number(device.duration_h) || 1, 1) * 60 * 60 * 1000;
  return Date.now() < started + durationMs;
}

export function DeviceRunningToggle({ device, onChange, disabled }) {
  const running = isDeviceRunningNow(device);
  return (
    <ToggleRow
      label="Şu an çalışıyor"
      detail={running ? 'Mevcut tüketim hesabına eklenir; bugün yeniden planlanmaz.' : 'Cihaz şu anda kapalı.'}
      value={running}
      disabled={disabled}
      onValueChange={(next) => onChange({
        is_running: next,
        status_updated_at: next ? new Date().toISOString() : null,
      })}
    />
  );
}

export function DeviceStatusControls({ device, onChange, disabled }) {
  return (
    <View style={{ marginTop: spacing.s }}>
      <DeviceRunningToggle device={device} onChange={onChange} disabled={disabled} />
      <ToggleRow
        label="Planlamaya dahil"
        detail={device.enabled === false ? 'Wattra bu cihazın saatini değiştirmez.' : 'Uygun saati optimizer belirleyebilir.'}
        value={device.enabled !== false}
        disabled={disabled}
        onValueChange={(enabled) => onChange({ enabled })}
      />
    </View>
  );
}

export function FlexibilityToggle({ value, onChange, disabled }) {
  return (
    <ToggleRow
      label="Çalışması bölünebilir"
      detail="EV şarjı ve pompalar gibi cihazlar ucuz saatlerde durup devam edebilir."
      value={value === 'interruptible'}
      disabled={disabled}
      onValueChange={(enabled) => onChange(enabled ? 'interruptible' : 'shiftable')}
    />
  );
}

export function ManualDeviceForm({ existingNames = [], onAdd, onCancel }) {
  const [name, setName] = useState('');
  const [kwh, setKwh] = useState('');
  const [power, setPower] = useState('');
  const [duration, setDuration] = useState('1');
  const [earliest, setEarliest] = useState('0');
  const [latest, setLatest] = useState('23');
  const [flexibility, setFlexibility] = useState('shiftable');
  const [error, setError] = useState('');

  const add = () => {
    const parsedKwh = Number(String(kwh).replace(',', '.'));
    const parsedPower = power.trim() ? Number(String(power).replace(',', '.')) : null;
    const parsedDuration = Number(duration);
    const parsedEarliest = Number(earliest);
    const parsedLatest = Number(latest);
    const normalizedNames = existingNames.map((item) => item.trim().toLocaleLowerCase('tr-TR'));

    if (!name.trim()) {
      setError('Cihaz adını yaz.');
      return;
    }
    if (normalizedNames.includes(name.trim().toLocaleLowerCase('tr-TR'))) {
      setError('Bu isimde bir cihaz zaten kayıtlı.');
      return;
    }
    if (!(parsedKwh > 0) || !(parsedDuration >= 1 && parsedDuration <= 12)) {
      setError('Tüketim ve süre için geçerli değerler gir.');
      return;
    }
    if (parsedPower !== null && !(parsedPower > 0)) {
      setError('Güç değerini boş bırak veya sıfırdan büyük gir.');
      return;
    }
    if (![parsedEarliest, parsedLatest].every(Number.isInteger)
        || parsedEarliest < 0 || parsedLatest > 23 || parsedEarliest > parsedLatest
        || parsedEarliest + Math.ceil(parsedDuration) - 1 > parsedLatest) {
      setError('Saat aralığı 00-23 içinde olmalı ve çalışma süresi bu aralığa sığmalı.');
      return;
    }

    onAdd({
      name: name.trim(),
      category: 'custom',
      kwh: parsedKwh,
      power_kw: parsedPower,
      duration_h: Math.ceil(parsedDuration),
      earliest: parsedEarliest,
      latest: parsedLatest,
      flexibility,
      source: 'Kullanıcı tarafından girildi',
      enabled: true,
      is_running: false,
      status_updated_at: null,
      user_defined: true,
    });
  };

  return (
    <View style={{
      marginTop: spacing.m, paddingTop: spacing.m,
      borderTopWidth: 1, borderTopColor: colors.line,
    }}>
      <Text style={[text.subtitle, { marginBottom: spacing.m }]}>Kendi cihazını ekle</Text>
      <TextInput
        value={name}
        onChangeText={setName}
        placeholder="Örn. seramik fırını"
        placeholderTextColor={colors.faint}
        accessibilityLabel="Cihaz adı"
        style={[inputField, { marginBottom: spacing.s }]}
      />
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.s }}>
        <NumericField label="Tüketim" value={kwh} onChange={setKwh} unit="kWh" />
        <NumericField label="Güç" value={power} onChange={setPower} unit="kW" />
        <NumericField label="Süre" value={duration} onChange={setDuration} unit="saat" />
        <NumericField label="En erken" value={earliest} onChange={setEarliest} unit="sa" />
        <NumericField label="En geç bitiş" value={latest} onChange={setLatest} unit="sa" />
      </View>
      <View style={{ marginTop: spacing.s }}>
        <FlexibilityToggle value={flexibility} onChange={setFlexibility} />
      </View>
      <InlineNotice tone="error" message={error} />
      <View style={{ flexDirection: 'row', gap: spacing.s, marginTop: spacing.s }}>
        <Pressable
          onPress={add}
          accessibilityRole="button"
          accessibilityLabel="Cihazı ekle"
          style={[primaryButton, { flex: 1, minHeight: TOUCH }]}
        >
          <Text style={primaryButtonText}>Cihazı ekle</Text>
        </Pressable>
        <Pressable
          onPress={onCancel}
          accessibilityRole="button"
          accessibilityLabel="Cihaz eklemeyi iptal et"
          style={{
            minHeight: TOUCH, paddingHorizontal: spacing.m,
            borderRadius: 12, borderWidth: 1, borderColor: colors.border,
            alignItems: 'center', justifyContent: 'center',
          }}
        >
          <Text style={{ color: colors.ink, fontFamily: font.medium }}>Vazgeç</Text>
        </Pressable>
      </View>
    </View>
  );
}
