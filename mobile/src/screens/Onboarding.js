// Onboarding: setup in 4 steps → first suggestion in 5 minutes.
// Only asks what the user KNOWS: home or business, which city, panel power,
// monthly bill and the flexible devices at home. Hourly consumption data is
// NOT requested — the backend estimates it from the bill (calibration).

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator, Pressable, ScrollView, Text, TextInput, View,
} from 'react-native';
import { api } from '../api';
import { alertUser } from '../notify';
import { LogoMark, Wordmark } from '../components/Brand';
import {
  primaryButton, primaryButtonText, spacing, font, card, colors, text,
} from '../theme';

const CITIES = [
  { name: 'İstanbul', lat: 41.01, lon: 28.98 },
  { name: 'Ankara', lat: 39.93, lon: 32.86 },
  { name: 'İzmir', lat: 38.42, lon: 27.14 },
  { name: 'Antalya', lat: 36.9, lon: 30.7 },
  { name: 'Bursa', lat: 40.19, lon: 29.06 },
  { name: 'Adana', lat: 37.0, lon: 35.32 },
  { name: 'Konya', lat: 37.87, lon: 32.48 },
  { name: 'Gaziantep', lat: 37.07, lon: 37.38 },
  { name: 'Kayseri', lat: 38.72, lon: 35.49 },
  { name: 'Şanlıurfa', lat: 37.16, lon: 38.79 },
  { name: 'Denizli', lat: 37.78, lon: 29.09 },
  { name: 'Muğla', lat: 37.22, lon: 28.36 },
];

function Option({ label, selected, onPress, small }) {
  return (
    <Pressable
      onPress={onPress}
      style={{
        paddingVertical: small ? 9 : 14,
        paddingHorizontal: 15,
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

function NumberInput({ label, value, setValue, unit }) {
  return (
    <View style={{ marginBottom: spacing.m }}>
      <Text style={[text.body, { marginBottom: 6 }]}>{label}</Text>
      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
        <TextInput
          value={value}
          onChangeText={setValue}
          keyboardType="numeric"
          style={{
            borderWidth: 1, borderColor: colors.border, borderRadius: 12,
            padding: 13, fontSize: 17, width: 120,
            backgroundColor: colors.input, color: colors.ink,
            fontFamily: font.number,
          }}
        />
        <Text style={[text.body, { marginLeft: spacing.s }]}>{unit}</Text>
      </View>
    </View>
  );
}

export default function Onboarding({ onDone }) {
  const [step, setStep] = useState(0);
  const [type, setType] = useState('home');
  const [city, setCity] = useState(CITIES[2]);
  const [panelKw, setPanelKw] = useState('5');
  const [batteryKwh, setBatteryKwh] = useState('0');
  const [bill, setBill] = useState('300');
  const [tariff, setTariff] = useState('single');
  const [catalog, setCatalog] = useState([]);
  const [selectedDevices, setSelectedDevices] = useState([]);
  const [locationLoading, setLocationLoading] = useState(false);
  const [weatherCheck, setWeatherCheck] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.deviceCatalog().then((d) => setCatalog(d.devices)).catch(() => {});
  }, []);

  const isDeviceSelected = (name) => selectedDevices.some((d) => d.name === name);
  const toggleDevice = (device) =>
    setSelectedDevices((current) =>
      isDeviceSelected(device.name) ? current.filter((d) => d.name !== device.name) : [...current, device]
    );

  const useCurrentLocation = async () => {
    setLocationLoading(true);
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== 'granted') {
        alertUser('Konum izni gerekli', 'Konum izni vermezsen listeden il seçerek devam edebilirsin.');
        return;
      }
      const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      let label = 'Konumum';
      try {
        const [place] = await Location.reverseGeocodeAsync(position.coords);
        label = place?.city || place?.subregion || place?.region || label;
      } catch {
        // Reverse geocoding is only a label; coordinates are enough for the model.
      }
      const nextCity = {
        name: label,
        lat: Number(position.coords.latitude.toFixed(4)),
        lon: Number(position.coords.longitude.toFixed(4)),
      };
      setCity(nextCity);
      const check = await api.weatherCheck({
        lat: nextCity.lat,
        lon: nextCity.lon,
        panel_kw: parseFloat(panelKw) || 5,
        day: 'today',
      });
      setWeatherCheck(check);
    } catch (err) {
      alertUser('Konum alınamadı', `Konum veya hava durumu kontrolü başarısız oldu.\n\n${err.message}`);
    } finally {
      setLocationLoading(false);
    }
  };

  const finish = async () => {
    setSubmitting(true);
    try {
      const battery = parseFloat(batteryKwh) || 0;
      const resp = await api.register({
        user_type: type,
        city: city.name,
        lat: city.lat,
        lon: city.lon,
        panel_kw: parseFloat(panelKw) || 5,
        battery_kwh: battery,
        battery_power_kw: battery > 0 ? Math.min(battery / 2, 5) : 0,
        monthly_bill_kwh: parseFloat(bill) || 300,
        tariff_type: tariff,
        devices: selectedDevices,
      });
      await AsyncStorage.setItem('userId', String(resp.user_id));
      onDone(resp.user_id);
    } catch (err) {
      alertUser(
        'Bağlantı sorunu',
        `Sunucuya ulaşılamadı. Ayarlar > API adresini kontrol edin.\n\n${err.message}`
      );
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
      <Text style={[text.title, { marginVertical: spacing.m }]}>Hangi ilde?</Text>
      <Pressable
        disabled={locationLoading}
        onPress={useCurrentLocation}
        style={[primaryButton, {
          alignSelf: 'flex-start', minWidth: 190, marginBottom: spacing.m,
          opacity: locationLoading ? 0.7 : 1,
        }]}
      >
        {locationLoading ? (
          <ActivityIndicator color={colors.amberInk} />
        ) : (
          <Text style={primaryButtonText}>Konumumu kullan</Text>
        )}
      </Pressable>
      {weatherCheck && (
        <View style={{
          borderWidth: 1, borderColor: colors.border, borderRadius: 12,
          backgroundColor: colors.input, padding: spacing.m, marginBottom: spacing.m,
        }}>
          <Text style={text.subtitle}>{city.name} hava kontrolü hazır</Text>
          <Text style={[text.body, { marginTop: 4, fontSize: 13.5 }]}>
            Bugün {weatherCheck.estimated_production_kwh.toFixed(1)} kWh üretim tahmini,
            tepe güneş {String(weatherCheck.peak_hour).padStart(2, '0')}:00.
            Bulut ortalaması %{weatherCheck.avg_cloud_pct.toFixed(0)}.
          </Text>
          <Text style={[text.small, { marginTop: 6 }]}>
            Model: {weatherCheck.production_model_version}
          </Text>
        </View>
      )}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
        {CITIES.map((c) => (
          <Option key={c.name} small label={c.name}
                  selected={city.name === c.name} onPress={() => setCity(c)} />
        ))}
      </View>
    </View>,

    <View key="panel">
      <Text style={[text.title, { marginBottom: spacing.m }]}>Güneş sistemin</Text>
      <NumberInput label="Panel gücü (faturanda veya sözleşmende yazar)"
                   value={panelKw} setValue={setPanelKw} unit="kW" />
      <NumberInput label="Batarya kapasitesi (yoksa 0 bırak)"
                   value={batteryKwh} setValue={setBatteryKwh} unit="kWh" />
      <Text style={text.small}>
        Bataryan olmasa da Voltaic cihazlarını güneş saatlerine planlayarak tasarruf sağlar.
      </Text>
    </View>,

    <View key="bill">
      <Text style={[text.title, { marginBottom: spacing.m }]}>Elektrik faturan</Text>
      <NumberInput label="Aylık tüketimin (faturada 'kWh' yazan satır)"
                   value={bill} setValue={setBill} unit="kWh / ay" />
      <Text style={[text.body, { marginBottom: spacing.s }]}>Tarifen hangisi?</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
        <Option label="Tek zamanlı (bilmiyorum)" selected={tariff === 'single'}
                onPress={() => setTariff('single')} />
        <Option label="Üç zamanlı" selected={tariff === 'three_zone'}
                onPress={() => setTariff('three_zone')} />
      </View>
      <Text style={text.small}>
        Çoğu abonelik tek zamanlıdır. Üç zamanlıda gece ucuz, 17-22 arası pahalıdır —
        emin değilsen faturanda "T1/T2/T3" satırları olup olmadığına bak.
      </Text>
    </View>,

    <View key="device">
      <Text style={[text.title, { marginBottom: spacing.s }]}>Hangi cihazların var?</Text>
      <Text style={[text.body, { marginBottom: spacing.m }]}>
        Zamanını kaydırabileceğin cihazları seç — Voltaic bunları en ucuz saate planlayacak.
      </Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
        {catalog
          .filter((c) => type === 'business' || !c.name.includes('işyeri'))
          .map((device) => (
            <Option key={device.name} small label={device.name}
                    selected={isDeviceSelected(device.name)} onPress={() => toggleDevice(device)} />
          ))}
      </View>
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

      <View style={[card, { minHeight: 320 }]}>{steps[step]}</View>

      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Pressable disabled={step === 0} onPress={() => setStep(step - 1)}
                   style={{ padding: 14, opacity: step === 0 ? 0.25 : 1 }}>
          <Text style={[text.body, { fontFamily: font.medium }]}>← Geri</Text>
        </Pressable>
        <Pressable
          disabled={submitting}
          onPress={() => (step < steps.length - 1 ? setStep(step + 1) : finish())}
          style={[primaryButton, { minWidth: 150 }]}
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
