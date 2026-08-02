import * as Location from 'expo-location';
import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator, Linking, Modal, Pressable, ScrollView, Text, TextInput, View,
} from 'react-native';
import PROVINCES from '../data/turkey-provinces.json';
import DISTRICTS_BY_PROVINCE from '../data/turkey-districts.json';
import { api } from '../api';
import { InlineNotice, TOUCH } from './States';
import {
  primaryButton, primaryButtonText, spacing, font, colors, text,
} from '../theme';

const LOCATION_TIMEOUT_MS = 15000;
const GEOCODE_TIMEOUT_MS = 5000;

function withTimeout(promise, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('LOCATION_TIMEOUT')), timeoutMs);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        clearTimeout(timer);
        reject(error);
      }
    );
  });
}

function normalize(value) {
  return String(value || '')
    .toLocaleLowerCase('tr-TR')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

function inferProvince(value) {
  const parts = String(value?.name || '').split(',').map((part) => part.trim());
  const candidates = [value?.province, parts[parts.length - 1], value?.name];
  return PROVINCES.find((province) =>
    candidates.some((candidate) => normalize(candidate) === normalize(province.name))) || null;
}

function inferDistrict(value) {
  if (value?.district) return value.district;
  const parts = String(value?.name || '').split(',').map((part) => part.trim());
  return parts.length > 1 ? parts[0] : null;
}

function localAddress(place) {
  const province = place?.region || place?.city || null;
  const districtCandidates = [place?.subregion, place?.district, place?.city];
  const district = districtCandidates.find((candidate) =>
    candidate && normalize(candidate) !== normalize(province)) || null;
  const label = district && province ? `${district}, ${province}` : district || province;
  return label ? { province, district, label } : null;
}

function SelectField({ label, value, placeholder, onPress, disabled }) {
  return (
    <View style={{ flex: 1, minWidth: 130 }}>
      <Text style={[text.small, { marginBottom: spacing.xs }]}>{label}</Text>
      <Pressable
        onPress={onPress}
        disabled={disabled}
        accessibilityRole="button"
        accessibilityLabel={`${label} seç`}
        accessibilityState={{ disabled: !!disabled }}
        style={{
          minHeight: TOUCH, borderRadius: 12, borderWidth: 1,
          borderColor: value ? colors.amber : colors.border,
          backgroundColor: colors.input, paddingHorizontal: 13,
          justifyContent: 'center', opacity: disabled ? 0.45 : 1,
        }}
      >
        <Text
          numberOfLines={1}
          style={{
            color: value ? colors.ink : colors.faint,
            fontFamily: value ? font.medium : font.body,
            fontSize: 14,
          }}
        >
          {value || placeholder}
        </Text>
      </Pressable>
    </View>
  );
}

function SelectionModal({ mode, province, onProvince, onDistrict, onClose }) {
  const [search, setSearch] = useState('');
  const isProvince = mode === 'province';
  const options = useMemo(() => {
    const source = isProvince
      ? PROVINCES.map((item) => ({ key: item.code, label: item.name, value: item }))
      : (DISTRICTS_BY_PROVINCE[province?.code] || []).map((name) => ({
        key: name, label: name, value: name,
      }));
    const query = normalize(search.trim());
    return query ? source.filter((item) => normalize(item.label).includes(query)) : source;
  }, [isProvince, province, search]);

  useEffect(() => { setSearch(''); }, [mode]);

  return (
    <Modal
      visible={Boolean(mode)}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={{
        flex: 1, backgroundColor: 'rgba(5,8,14,0.82)',
        alignItems: 'center', justifyContent: 'center', padding: spacing.m,
      }}>
        <View style={{
          width: '100%', maxWidth: 480, maxHeight: '82%',
          backgroundColor: colors.surface, borderRadius: 16,
          borderWidth: 1, borderColor: colors.border, overflow: 'hidden',
        }}>
          <View style={{
            flexDirection: 'row', alignItems: 'center',
            paddingHorizontal: spacing.m, paddingTop: spacing.m,
          }}>
            <Text style={[text.title, { flex: 1, fontSize: 18 }]}>
              {isProvince ? 'İlini seç' : `${province?.name || ''} ilçesi`}
            </Text>
            <Pressable
              onPress={onClose}
              accessibilityRole="button"
              accessibilityLabel="Seçimi kapat"
              style={{ width: TOUCH, height: TOUCH, alignItems: 'center', justifyContent: 'center' }}
            >
              <Text style={{ color: colors.ink, fontSize: 24, lineHeight: 26 }}>×</Text>
            </Pressable>
          </View>
          <TextInput
            value={search}
            onChangeText={setSearch}
            placeholder={isProvince ? 'İl ara' : 'İlçe ara'}
            placeholderTextColor={colors.faint}
            autoCapitalize="words"
            accessibilityLabel={isProvince ? 'İl ara' : 'İlçe ara'}
            style={{
              marginHorizontal: spacing.m, marginBottom: spacing.s,
              minHeight: TOUCH, borderRadius: 12, borderWidth: 1,
              borderColor: colors.border, backgroundColor: colors.input,
              paddingHorizontal: 13, color: colors.ink,
              fontFamily: font.body, fontSize: 15,
            }}
          />
          <ScrollView keyboardShouldPersistTaps="handled">
            {options.map((option) => (
              <Pressable
                key={option.key}
                onPress={() => (isProvince ? onProvince(option.value) : onDistrict(option.value))}
                accessibilityRole="button"
                accessibilityLabel={option.label}
                style={{
                  minHeight: TOUCH, justifyContent: 'center',
                  paddingHorizontal: spacing.m, borderTopWidth: 1,
                  borderTopColor: colors.line,
                }}
              >
                <Text style={[text.body, { color: colors.ink }]}>{option.label}</Text>
              </Pressable>
            ))}
            {options.length === 0 ? (
              <Text style={[text.body, { padding: spacing.m }]}>Eşleşen yer bulunamadı.</Text>
            ) : null}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

/** Selects and stores the fixed installation coordinates. */
export default function LocationPicker({ value, onChange, placeLabel = 'Evinin' }) {
  const [gpsLoading, setGpsLoading] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [status, setStatus] = useState(null);
  const [mode, setMode] = useState(null);
  const [province, setProvince] = useState(() => inferProvince(value));
  const [district, setDistrict] = useState(() => inferDistrict(value));
  const busy = gpsLoading || resolving;

  useEffect(() => {
    const inferredProvince = inferProvince(value);
    if (inferredProvince) setProvince(inferredProvince);
    const inferredDistrict = inferDistrict(value);
    if (inferredDistrict) setDistrict(inferredDistrict);
  }, [value]);

  const applyResolvedLocation = (resolved) => {
    const nextProvince = PROVINCES.find((item) =>
      normalize(item.name) === normalize(resolved.province));
    if (nextProvince) setProvince(nextProvince);
    setDistrict(resolved.district || null);
    onChange({
      name: resolved.label,
      province: resolved.province,
      district: resolved.district,
      lat: Number(resolved.lat),
      lon: Number(resolved.lon),
    });
  };

  const resolveSelection = async (selectedProvince, selectedDistrict) => {
    setResolving(true);
    setStatus({ tone: 'info', loading: true, message: 'İlçe konumu hazırlanıyor…' });
    try {
      const resolved = await api.resolveLocation(selectedProvince.name, selectedDistrict);
      applyResolvedLocation(resolved);
      setStatus({
        tone: 'success',
        message: `${resolved.label} sistem konumu olarak seçildi.`,
      });
    } catch {
      setStatus({
        tone: 'error',
        message: 'İlçe konumu alınamadı. Bağlantını kontrol edip yeniden dene.',
        actionLabel: 'Tekrar dene',
        onAction: () => resolveSelection(selectedProvince, selectedDistrict),
      });
    } finally {
      setResolving(false);
    }
  };

  const useDeviceLocation = async () => {
    setGpsLoading(true);
    setStatus({ tone: 'info', loading: true, message: 'Konum izni kontrol ediliyor…' });
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== 'granted') {
        const canAsk = permission.canAskAgain;
        setStatus({
          tone: 'error',
          message: canAsk
            ? 'Konumu belirlemek için izin vermen gerekiyor.'
            : 'Konum iznini cihaz ayarlarından açıp yeniden dene.',
          actionLabel: canAsk ? 'Tekrar izin iste' : 'Ayarları aç',
          onAction: canAsk ? useDeviceLocation : () => Linking.openSettings(),
        });
        return;
      }

      setStatus({ tone: 'info', loading: true, message: `${placeLabel} konumu aranıyor…` });
      let position;
      let usedLastKnownPosition = false;
      try {
        position = await withTimeout(
          Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.High,
            mayShowUserSettingsDialog: true,
          }),
          LOCATION_TIMEOUT_MS
        );
      } catch {
        position = await Location.getLastKnownPositionAsync({
          maxAge: 5 * 60 * 1000,
          requiredAccuracy: 2000,
        });
        usedLastKnownPosition = Boolean(position);
        if (!position) throw new Error('LOCATION_UNAVAILABLE');
      }

      const lat = Number(position.coords.latitude.toFixed(6));
      const lon = Number(position.coords.longitude.toFixed(6));
      let resolved;
      try {
        resolved = await api.reverseLocation(lat, lon);
      } catch {
        try {
          const [place] = await withTimeout(
            Location.reverseGeocodeAsync(position.coords),
            GEOCODE_TIMEOUT_MS
          );
          const local = localAddress(place);
          if (local) resolved = { ...local, lat, lon };
        } catch {
          // Exact coordinates remain usable even if no address provider responds.
        }
      }

      if (!resolved) {
        resolved = {
          province: null,
          district: null,
          label: `GPS konumu (${lat.toFixed(4)}, ${lon.toFixed(4)})`,
          lat,
          lon,
        };
      }
      applyResolvedLocation(resolved);
      setStatus({
        tone: 'success',
        message: usedLastKnownPosition
          ? `${resolved.label} bulundu. Cihazının son konumu kullanıldı; doğru değilse yeniden dene.`
          : `${resolved.label} bulundu. ${placeLabel} konumu doğruysa devam edebilirsin.`,
      });
    } catch {
      setStatus({
        tone: 'error',
        message: 'Konum alınamadı. Konum servislerini kontrol et veya il ve ilçeni seç.',
        actionLabel: 'Tekrar dene',
        onAction: useDeviceLocation,
      });
    } finally {
      setGpsLoading(false);
    }
  };

  return (
    <View>
      <Text style={[text.small, { lineHeight: 18, marginBottom: spacing.m }]}>
        Bu konum hava ve güneş üretim tahminlerinde kullanılır. Yalnızca taşınırsan
        değiştirmen gerekir.
      </Text>
      <Pressable
        disabled={busy}
        onPress={useDeviceLocation}
        accessibilityRole="button"
        accessibilityLabel={`${placeLabel} konumunu cihazdan belirle`}
        style={[primaryButton, {
          alignSelf: 'flex-start', minWidth: 220, marginBottom: spacing.m,
          opacity: busy ? 0.7 : 1,
        }]}
      >
        {gpsLoading ? (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.s }}>
            <ActivityIndicator color={colors.amberInk} />
            <Text style={primaryButtonText}>Konum belirleniyor</Text>
          </View>
        ) : (
          <Text style={primaryButtonText}>Cihaz konumunu kullan</Text>
        )}
      </Pressable>

      <Text style={[text.small, { marginBottom: spacing.s }]}>Ya da elle seç</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.s, marginBottom: spacing.m }}>
        <SelectField
          label="İl"
          value={province?.name}
          placeholder="İl seç"
          disabled={busy}
          onPress={() => setMode('province')}
        />
        <SelectField
          label="İlçe"
          value={district}
          placeholder={province ? 'İlçe seç' : 'Önce il seç'}
          disabled={busy || !province}
          onPress={() => setMode('district')}
        />
      </View>

      <InlineNotice
        tone={status?.tone}
        loading={status?.loading}
        message={status?.message}
        actionLabel={status?.actionLabel}
        onAction={status?.onAction}
      />
      <Text style={[text.small, { marginBottom: spacing.m }]}>Konum: © OpenStreetMap katkıcıları</Text>

      <SelectionModal
        mode={mode}
        province={province}
        onClose={() => setMode(null)}
        onProvince={(selected) => {
          setProvince(selected);
          setDistrict(null);
          onChange(null);
          setMode('district');
          setStatus(null);
        }}
        onDistrict={(selected) => {
          setDistrict(selected);
          setMode(null);
          resolveSelection(province, selected);
        }}
      />
    </View>
  );
}
