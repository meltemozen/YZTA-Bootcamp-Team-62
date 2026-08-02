// Onboarding: setup in 4 steps → first suggestion in 5 minutes.
// Only asks what the user KNOWS: home or business, which city, panel power,
// monthly bill and the flexible devices at home. Hourly consumption data is
// NOT requested — the backend estimates it from the bill (calibration).

import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator, Pressable, ScrollView, Text, TextInput, View,
} from 'react-native';
import { api } from '../api';
import { LogoMark, Wordmark } from '../components/Brand';
import {
  DeviceStatusControls, ManualDeviceForm,
} from '../components/DeviceControls';
import LocationPicker from '../components/LocationPicker';
import {
  ErrorState, InlineNotice, LoadingState, TOUCH,
} from '../components/States';
import {
  primaryButton, primaryButtonText, spacing, font, card, colors, text,
} from '../theme';

const ONBOARDING_DRAFT_VERSION = 1;

function Option({ label, selected, onPress, small }) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      accessibilityLabel={label}
      style={{
        paddingVertical: small ? 12 : 14,
        paddingHorizontal: 15,
        minHeight: TOUCH,
        justifyContent: 'center',
        borderRadius: 12,
        borderWidth: 1.5,
        borderColor: selected ? colors.amber : colors.border,
        backgroundColor: selected ? colors.amberSoft : colors.input,
        marginBottom: spacing.s,
        marginRight: spacing.s,
      }}
    >
      <Text style={{
        fontFamily: selected ? font.semibold : font.body,
        fontSize: 14,
        color: selected ? colors.amber : colors.inkSecondary,
      }}>
        {label}
      </Text>
    </Pressable>
  );
}

function NumberInput({ label, value, setValue, unit, error, warning }) {
  const borderColor = error ? colors.critical : colors.border;
  return (
    <View style={{ marginBottom: spacing.m }}>
      <Text style={[text.body, { marginBottom: 6 }]}>{label}</Text>
      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
        <TextInput
          value={value}
          onChangeText={setValue}
          keyboardType="numeric"
          accessibilityLabel={label}
          accessibilityHint={unit}
          style={{
            borderWidth: 1, borderColor, borderRadius: 12,
            padding: 13, fontSize: 17, width: 120, minHeight: TOUCH,
            backgroundColor: colors.input, color: colors.ink,
            fontFamily: font.number,
          }}
        />
        <Text style={[text.body, { marginLeft: spacing.s }]}>{unit}</Text>
      </View>
      {error ? (
        <Text style={[text.small, { color: colors.critical, marginTop: 5 }]}
          accessibilityRole="alert">
          {error}
        </Text>
      ) : null}
      {!error && warning ? (
        <Text style={[text.small, { color: colors.amber, marginTop: 5 }]}>{warning}</Text>
      ) : null}
    </View>
  );
}

// Validation lives here rather than inline so the "can I continue?" check and
// the message under the field can never disagree. Ranges are physical/legal:
// residential rooftop net-metering is capped at 10 kW (config.py), and a
// household bill outside 30-5000 kWh/month is almost certainly a typo.
function validate({ panelKw, batteryKwh, bill, userType, tariff, singlePrice, dayPrice,
                    peakPrice, nightPrice, sellPrice }) {
  const errors = {};
  const warnings = {};

  const panel = parseFloat(panelKw.replace(',', '.'));
  if (!panelKw.trim() || Number.isNaN(panel)) {
    errors.panelKw = 'Panel gücünü yaz.';
  } else if (panel <= 0) {
    errors.panelKw = 'Panel gücü sıfırdan büyük olmalı.';
  } else if (panel > 100) {
    errors.panelKw = 'Bu değer çok yüksek görünüyor — kW cinsinden yazdığından emin ol.';
  } else if (userType === 'home' && panel > 10) {
    warnings.panelKw = 'Meskende mahsuplaşma sınırı 10 kW; üstü için ticari abonelik gerekir.';
  }

  const battery = parseFloat(batteryKwh.replace(',', '.'));
  if (!batteryKwh.trim() || Number.isNaN(battery)) {
    errors.batteryKwh = 'Bataryan yoksa 0 yaz.';
  } else if (battery < 0) {
    errors.batteryKwh = 'Negatif kapasite olamaz.';
  } else if (battery > 200) {
    errors.batteryKwh = 'Bu kapasite çok yüksek görünüyor — kWh cinsinden yazdığından emin ol.';
  }

  const monthly = parseFloat(bill.replace(',', '.'));
  if (!bill.trim() || Number.isNaN(monthly)) {
    errors.bill = 'Aylık tüketimini yaz (faturada "kWh" satırı).';
  } else if (monthly <= 0) {
    errors.bill = 'Tüketim sıfırdan büyük olmalı.';
  } else if (monthly < 30) {
    warnings.bill = 'Bu çok düşük — faturadaki TL tutarını değil, kWh değerini yaz.';
  } else if (monthly > 5000) {
    warnings.bill = 'Bu çok yüksek — aylık kWh yerine yıllık değeri yazmış olabilir misin?';
  }

  if (!tariff) {
    errors.tariff = 'Faturandaki tarife türünü seç.';
  }
  const requiredPrices = tariff === 'three_zone'
    ? [dayPrice, peakPrice, nightPrice]
    : tariff === 'single' ? [singlePrice] : [];
  if (requiredPrices.some((value) => {
    const parsed = parseFloat(value.replace(',', '.'));
    return !value.trim() || Number.isNaN(parsed) || parsed <= 0;
  })) {
    errors.tariff = 'Faturandaki geçerli birim fiyatları TL/kWh olarak gir.';
  }
  const parsedSell = parseFloat(sellPrice.replace(',', '.'));
  if (!sellPrice.trim() || Number.isNaN(parsedSell) || parsedSell < 0) {
    errors.tariff = 'Şebekeye satış bedelini gir; satış yoksa 0 yaz.';
  }

  return { errors, warnings };
}

export default function Onboarding({ userId, onDone }) {
  const draftKey = `wattra_onboarding_draft_${userId || 'legacy'}`;
  const [step, setStep] = useState(0);
  const [type, setType] = useState(null);
  const [city, setCity] = useState(null);
  const [panelKw, setPanelKw] = useState('');
  const [batteryKwh, setBatteryKwh] = useState('0');
  const [bill, setBill] = useState('');
  const [tariff, setTariff] = useState(null);
  const [singlePrice, setSinglePrice] = useState('');
  const [dayPrice, setDayPrice] = useState('');
  const [peakPrice, setPeakPrice] = useState('');
  const [nightPrice, setNightPrice] = useState('');
  const [sellPrice, setSellPrice] = useState('');
  const [catalog, setCatalog] = useState([]);
  const [selectedDevices, setSelectedDevices] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [registerError, setRegisterError] = useState(null);
  const [catalogError, setCatalogError] = useState(null);
  const [draftReady, setDraftReady] = useState(false);
  const [draftRestored, setDraftRestored] = useState(false);
  const [showManualDevice, setShowManualDevice] = useState(false);

  useEffect(() => {
    let active = true;

    const restoreDraft = async () => {
      try {
        const raw = await AsyncStorage.getItem(draftKey);
        if (!raw || !active) return;

        const draft = JSON.parse(raw);
        if (draft.version !== ONBOARDING_DRAFT_VERSION) return;

        setStep(Math.max(0, Math.min(3, Number(draft.step) || 0)));
        setType(['home', 'business'].includes(draft.type) ? draft.type : null);
        if (draft.city && Number.isFinite(draft.city.lat) && Number.isFinite(draft.city.lon)) {
          setCity(draft.city);
        }
        setPanelKw(typeof draft.panelKw === 'string' ? draft.panelKw : '');
        setBatteryKwh(typeof draft.batteryKwh === 'string' ? draft.batteryKwh : '0');
        setBill(typeof draft.bill === 'string' ? draft.bill : '');
        setTariff(['single', 'three_zone'].includes(draft.tariff) ? draft.tariff : null);
        setSinglePrice(typeof draft.singlePrice === 'string' ? draft.singlePrice : '');
        setDayPrice(typeof draft.dayPrice === 'string' ? draft.dayPrice : '');
        setPeakPrice(typeof draft.peakPrice === 'string' ? draft.peakPrice : '');
        setNightPrice(typeof draft.nightPrice === 'string' ? draft.nightPrice : '');
        setSellPrice(typeof draft.sellPrice === 'string' ? draft.sellPrice : '');
        setSelectedDevices(Array.isArray(draft.selectedDevices) ? draft.selectedDevices : []);
        setDraftRestored(true);
      } catch {
        await AsyncStorage.removeItem(draftKey).catch(() => {});
      } finally {
        if (active) setDraftReady(true);
      }
    };

    restoreDraft();
    return () => { active = false; };
  }, [draftKey]);

  useEffect(() => {
    if (!draftReady) return undefined;

    const timer = setTimeout(() => {
      const draft = {
        version: ONBOARDING_DRAFT_VERSION,
        step,
        type,
        city,
        panelKw,
        batteryKwh,
        bill,
        tariff,
        singlePrice,
        dayPrice,
        peakPrice,
        nightPrice,
        sellPrice,
        selectedDevices,
      };
      AsyncStorage.setItem(draftKey, JSON.stringify(draft)).catch(() => {});
    }, 250);

    return () => clearTimeout(timer);
  }, [
    batteryKwh, bill, city, dayPrice, draftKey, draftReady, nightPrice, panelKw,
    peakPrice, selectedDevices, sellPrice, singlePrice, step, tariff, type,
  ]);

  const loadCatalog = useCallback(async () => {
    setCatalogError(null);
    try {
      setCatalog((await api.deviceCatalog()).devices);
    } catch (e) {
      setCatalogError(e.message);
    }
  }, []);

  useEffect(() => { loadCatalog(); }, [loadCatalog]);

  const isDeviceSelected = (name) => selectedDevices.some((d) => d.name === name);
  const toggleDevice = (device) =>
    setSelectedDevices((current) =>
      isDeviceSelected(device.name)
        ? current.filter((d) => d.name !== device.name)
        : [...current, {
          ...device,
          enabled: true,
          is_running: false,
          status_updated_at: null,
          user_defined: false,
        }]
    );
  const updateSelectedDevice = (name, patch) =>
    setSelectedDevices((current) => current.map((device) =>
      device.name === name ? { ...device, ...patch } : device));

  const { errors, warnings } = validate({
    panelKw, batteryKwh, bill, userType: type, tariff,
    singlePrice, dayPrice, peakPrice, nightPrice, sellPrice,
  });
  // Which fields must be valid before leaving each step.
  const STEP_FIELDS = [[], ['panelKw', 'batteryKwh'], ['bill', 'tariff'], []];
  const stepBlocked = (step === 0 && (!type || !city))
    || STEP_FIELDS[step].some((field) => errors[field]);

  const finish = async () => {
    setSubmitting(true);
    setRegisterError(null);
    try {
      const battery = parseFloat(batteryKwh.replace(',', '.')) || 0;
      const profile = {
        user_type: type,
        city: city.name,
        lat: city.lat,
        lon: city.lon,
        panel_kw: parseFloat(panelKw.replace(',', '.')),
        battery_kwh: battery,
        battery_power_kw: battery > 0 ? Math.min(battery / 2, 5) : 0,
        monthly_bill_kwh: parseFloat(bill.replace(',', '.')),
        tariff_type: tariff,
        custom_tariff: tariff === 'three_zone' ? {
          single: null,
          day: parseFloat(dayPrice.replace(',', '.')),
          peak: parseFloat(peakPrice.replace(',', '.')),
          night: parseFloat(nightPrice.replace(',', '.')),
          sell: parseFloat(sellPrice.replace(',', '.')),
        } : {
          single: parseFloat(singlePrice.replace(',', '.')),
          day: null,
          peak: null,
          night: null,
          sell: parseFloat(sellPrice.replace(',', '.')),
        },
        devices: selectedDevices,
      };
      // If userId is provided (auth flow), update the existing profile.
      // Otherwise fall back to the legacy register flow.
      if (userId) {
        await api.authUpdateMe({ profile });
        await AsyncStorage.removeItem(draftKey).catch(() => {});
        onDone(userId);
      } else {
        const resp = await api.register(profile);
        await AsyncStorage.setItem('userId', String(resp.user_id));
        await AsyncStorage.removeItem(draftKey).catch(() => {});
        onDone(resp.user_id);
      }
    } catch (err) {
      setRegisterError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const steps = [
    <View key="type">
      <Text style={[text.title, { marginBottom: spacing.m }]}>Panelin nerede kurulu?</Text>
      <View style={{ flexDirection: 'row' }}>
        <Option label="Evim" selected={type === 'home'} onPress={() => setType('home')} />
        <Option label="İşyerim" selected={type === 'business'} onPress={() => setType('business')} />
      </View>
      <Text style={[text.title, { marginVertical: spacing.m }]}>Sistemin hangi konumda?</Text>
      <LocationPicker
        value={city}
        onChange={setCity}
        placeLabel={type === 'business' ? 'İşyerinin' : 'Evinin'}
      />
    </View>,

    <View key="panel">
      <Text style={[text.title, { marginBottom: spacing.m }]}>Güneş sistemin</Text>
      <NumberInput label="Panel gücü (faturanda veya sözleşmende yazar)"
        value={panelKw} setValue={setPanelKw} unit="kW"
        error={errors.panelKw} warning={warnings.panelKw} />
      <NumberInput label="Batarya kapasitesi (yoksa 0 bırak)"
        value={batteryKwh} setValue={setBatteryKwh} unit="kWh"
        error={errors.batteryKwh} warning={warnings.batteryKwh} />
      <Text style={text.small}>
        Bataryan olmasa da Wattra cihazlarını güneş saatlerine planlayarak tasarruf sağlar.
      </Text>
    </View>,

    <View key="bill">
      <Text style={[text.title, { marginBottom: spacing.m }]}>Elektrik faturan</Text>
      <NumberInput label="Aylık tüketimin (faturada 'kWh' yazan satır)"
        value={bill} setValue={setBill} unit="kWh / ay"
        error={errors.bill} warning={warnings.bill} />
      <Text style={[text.body, { marginBottom: spacing.s }]}>Tarifen hangisi?</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
        <Option label="Tek zamanlı" selected={tariff === 'single'}
          onPress={() => setTariff('single')} />
        <Option label="Üç zamanlı" selected={tariff === 'three_zone'}
          onPress={() => setTariff('three_zone')} />
      </View>
      {tariff === 'single' && (
        <NumberInput label="Faturandaki birim fiyat" value={singlePrice}
          setValue={setSinglePrice} unit="TL / kWh" />
      )}
      {tariff === 'three_zone' && (
        <>
          <NumberInput label="Gündüz birim fiyatı (06-17)" value={dayPrice}
            setValue={setDayPrice} unit="TL / kWh" />
          <NumberInput label="Puant birim fiyatı (17-22)" value={peakPrice}
            setValue={setPeakPrice} unit="TL / kWh" />
          <NumberInput label="Gece birim fiyatı (22-06)" value={nightPrice}
            setValue={setNightPrice} unit="TL / kWh" />
        </>
      )}
      {tariff && (
        <NumberInput label="Şebekeye satış bedeli (satış yoksa 0)" value={sellPrice}
          setValue={setSellPrice} unit="TL / kWh" />
      )}
      {errors.tariff && tariff ? (
        <Text style={[text.small, { color: colors.critical, marginBottom: spacing.s }]}>
          {errors.tariff}
        </Text>
      ) : null}
      <Text style={text.small}>
        Tarife türü ve vergiler dahil birim fiyatlar faturandaki tüketim detayında yer alır.
      </Text>
    </View>,

    <View key="device">
      <Text style={[text.title, { marginBottom: spacing.s }]}>Hangi cihazların var?</Text>
      <Text style={[text.body, { marginBottom: spacing.m }]}>
        Zamanını kaydırabileceğin cihazları seç — Wattra bunları en ucuz saate planlayacak.
      </Text>
      {catalogError ? (
        <ErrorState
          title="Cihaz listesi yüklenemedi"
          message="Cihaz listesi şu anda alınamadı. Cihaz seçmeden de devam edebilirsin;
                   sonradan Ayarlar'dan ekleyebilirsin."
          hint={catalogError}
          onRetry={loadCatalog}
        />
      ) : catalog.length === 0 ? (
        <LoadingState label="Cihaz listesi yükleniyor…" />
      ) : (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
          {catalog
            .filter((c) => type === 'business' || !c.name.includes('işyeri'))
            .map((device) => (
              <Option key={device.name} small label={device.name}
                selected={isDeviceSelected(device.name)} onPress={() => toggleDevice(device)} />
            ))}
        </View>
      )}
      {catalog.length > 0 && selectedDevices.length === 0 && (
        <Text style={[text.small, { marginTop: spacing.s, color: colors.amber }]}>
          Hiç cihaz seçmezsen plan boş kalır — en az bir tane seçmeni öneririz.
        </Text>
      )}
      <Pressable
        onPress={() => setShowManualDevice(true)}
        accessibilityRole="button"
        accessibilityLabel="Kendi cihazını ekle"
        style={{
          minHeight: TOUCH, borderRadius: 12, borderWidth: 1,
          borderColor: colors.amber, alignItems: 'center', justifyContent: 'center',
          paddingHorizontal: spacing.m, marginTop: spacing.m,
        }}
      >
        <Text style={{ color: colors.amber, fontFamily: font.semibold, fontSize: 14 }}>
          + Kendi cihazını ekle
        </Text>
      </Pressable>
      {showManualDevice ? (
        <ManualDeviceForm
          existingNames={selectedDevices.map((device) => device.name)}
          onCancel={() => setShowManualDevice(false)}
          onAdd={(device) => {
            setSelectedDevices((current) => [...current, device]);
            setShowManualDevice(false);
          }}
        />
      ) : null}
      {selectedDevices.length > 0 ? (
        <View style={{
          marginTop: spacing.m, paddingTop: spacing.m,
          borderTopWidth: 1, borderTopColor: colors.line,
        }}>
          <Text style={[text.small, { marginBottom: spacing.s }]}>Seçtiğin cihazlar</Text>
          {selectedDevices.map((device) => (
            <View key={device.name} style={{
              paddingVertical: spacing.s, borderBottomWidth: 1, borderBottomColor: colors.line,
            }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.s }}>
                <Text style={[text.subtitle, { flex: 1 }]}>{device.name}</Text>
                {device.user_defined ? (
                  <Pressable
                    onPress={() => setSelectedDevices((current) =>
                      current.filter((item) => item.name !== device.name))}
                    accessibilityRole="button"
                    accessibilityLabel={`${device.name} cihazını kaldır`}
                    style={{ minHeight: TOUCH, justifyContent: 'center', paddingHorizontal: spacing.s }}
                  >
                    <Text style={{ color: colors.critical, fontFamily: font.medium }}>Kaldır</Text>
                  </Pressable>
                ) : null}
              </View>
              <DeviceStatusControls
                device={device}
                onChange={(patch) => updateSelectedDevice(device.name, patch)}
              />
            </View>
          ))}
        </View>
      ) : null}
    </View>,
  ];

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.page }}
      contentContainerStyle={{ padding: spacing.l, paddingTop: 64 }}>
      {/* Brand hero */}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 6 }}>
        <LogoMark size={40} />
        <View>
          <Wordmark size={26} />
          <Text style={[text.small, { marginTop: 1 }]}>Çatındaki güneş, akıllıca yönetilsin</Text>
        </View>
      </View>

      {/* Progress bar */}
      <View style={{
        height: 4, backgroundColor: colors.input, borderRadius: 2,
        marginTop: spacing.m, marginBottom: spacing.l, overflow: 'hidden',
      }}>
        <View style={{
          height: 4, borderRadius: 2, backgroundColor: colors.amber,
          width: `${((step + 1) / steps.length) * 100}%`,
        }} />
      </View>

      {draftRestored ? (
        <InlineNotice
          tone="info"
          message="Kuruluma kaldığın yerden devam ediyorsun."
        />
      ) : null}

      <View style={[card, { minHeight: 320 }]}>{steps[step]}</View>

      {registerError && (
        <ErrorState
          title="Kurulum tamamlanamadı"
          message="Kurulum şu anda tamamlanamadı. Girdiklerin duruyor."
          hint="Bağlantını kontrol edip tekrar dene."
          onRetry={finish}
        />
      )}

      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Pressable disabled={step === 0} onPress={() => setStep(step - 1)}
          accessibilityRole="button"
          accessibilityLabel="Önceki adım"
          accessibilityState={{ disabled: step === 0 }}
          style={{
            padding: 14, minHeight: TOUCH, justifyContent: 'center',
            opacity: step === 0 ? 0.25 : 1
          }}>
          <Text style={[text.body, { fontFamily: font.medium }]}>← Geri</Text>
        </Pressable>
        <Pressable
          disabled={submitting || stepBlocked}
          onPress={() => (step < steps.length - 1 ? setStep(step + 1) : finish())}
          accessibilityRole="button"
          accessibilityLabel={step < steps.length - 1 ? 'Sonraki adım' : 'Kurulumu tamamla'}
          accessibilityState={{ disabled: submitting || stepBlocked }}
          style={[primaryButton, {
            minWidth: 150, minHeight: TOUCH, justifyContent: 'center',
            opacity: submitting || stepBlocked ? 0.4 : 1,
          }]}
        >
          {submitting ? (
            <ActivityIndicator color={colors.amberInk} />
          ) : (
            <Text style={primaryButtonText}>
              {step < steps.length - 1 ? 'Devam' : 'Başla'}
            </Text>
          )}
        </Pressable>
      </View>
    </ScrollView>
  );
}
