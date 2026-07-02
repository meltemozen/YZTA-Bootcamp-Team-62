// Bugün ekranı: amber gradyan hero (tasarruf) + üretim/tüketim grafiği +
// plan kartları + proaktif uyarılar. Plan deterministik uçtan gelir.

import { LinearGradient } from 'expo-linear-gradient';
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator, Pressable, RefreshControl, ScrollView, Text, View,
} from 'react-native';
import { api, aralikTL } from '../api';
import GunlukGrafik from '../components/GunlukGrafik';
import { GunesIkon, YaprakIkon } from '../components/Ikonlar';
import { EkranBasligi } from '../components/Marka';
import PlanKarti from '../components/PlanKarti';
import { bosluk, font, kart, renk, yazi } from '../theme';

function GunSecici({ gun, setGun }) {
  return (
    <View style={{
      flexDirection: 'row', backgroundColor: renk.girdi, borderRadius: 20,
      borderWidth: 1, borderColor: renk.kenar, padding: 3,
    }}>
      {[['bugun', 'Bugün'], ['yarin', 'Yarın']].map(([deger, etiket]) => (
        <Pressable
          key={deger}
          onPress={() => setGun(deger)}
          style={{
            paddingVertical: 6, paddingHorizontal: 16, borderRadius: 17,
            backgroundColor: gun === deger ? renk.amber : 'transparent',
          }}
        >
          <Text style={{
            fontSize: 12.5, fontFamily: font.kalin,
            color: gun === deger ? renk.amberUstuMurekkep : renk.murekkepIkincil,
          }}>
            {etiket}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

export default function Bugun({ kullaniciId }) {
  const [gun, setGun] = useState('bugun');
  const [plan, setPlan] = useState(null);
  const [bildirimler, setBildirimler] = useState([]);
  const [hata, setHata] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(true);

  const yukle = useCallback(async () => {
    setYukleniyor(true);
    setHata(null);
    try {
      const [p, b] = await Promise.all([
        api.plan(kullaniciId, gun),
        api.bildirimler(kullaniciId).catch(() => ({ bildirimler: [] })),
      ]);
      setPlan(p);
      setBildirimler(b.bildirimler);
    } catch (e) {
      setHata(e.message);
    } finally {
      setYukleniyor(false);
    }
  }, [kullaniciId, gun]);

  useEffect(() => { yukle(); }, [yukle]);

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: renk.sayfa }}
      contentContainerStyle={{ padding: bosluk.m, paddingTop: 56, paddingBottom: 32 }}
      refreshControl={
        <RefreshControl refreshing={yukleniyor} onRefresh={yukle} tintColor={renk.amber} />
      }
    >
      <EkranBasligi baslik="Enerji Planın" sag={<GunSecici gun={gun} setGun={setGun} />} />

      {hata && (
        <View style={[kart, { borderColor: renk.kritik }]}>
          <Text style={[yazi.govde, { color: renk.kritik }]}>
            Sunucuya ulaşılamadı. Ayarlar sekmesinden API adresini kontrol et.
          </Text>
        </View>
      )}

      {yukleniyor && !plan && <ActivityIndicator style={{ marginTop: 48 }} color={renk.amber} />}

      {plan && (
        <>
          {/* Hero: gradyan tasarruf kartı */}
          <LinearGradient
            colors={[renk.amber, renk.amberKoyu]}
            start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
            style={{ borderRadius: 18, padding: bosluk.l, marginBottom: bosluk.m }}
          >
            <Text style={{
              fontFamily: font.kalin, fontSize: 11, letterSpacing: 1.2,
              textTransform: 'uppercase', color: 'rgba(34,21,0,0.65)',
            }}>
              Bu planla tahmini tasarruf
            </Text>
            <Text style={{
              fontFamily: font.baslik, fontSize: 40, color: renk.amberUstuMurekkep,
              letterSpacing: -0.5, marginTop: 2,
            }}>
              {aralikTL(plan.toplam_tasarruf_tl_min, plan.toplam_tasarruf_tl_max)}
            </Text>
            <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 8, gap: 6 }}>
              <YaprakIkon boyut={15} renk="rgba(34,21,0,0.75)" />
              <Text style={{ fontFamily: font.orta, fontSize: 13, color: 'rgba(34,21,0,0.75)' }}>
                {plan.co2_tasarruf_kg.toFixed(1)} kg CO₂
                {plan.ozet_veri.cevre?.araba_km
                  ? ` ≈ ${plan.ozet_veri.cevre.araba_km.toFixed(0)} km araba yolu`
                  : ''} · öz tüketim %{Math.round(plan.oz_tuketim_orani * 100)}
              </Text>
            </View>
            <Text style={{
              fontFamily: font.govde, fontSize: 11.5, color: 'rgba(34,21,0,0.6)', marginTop: 8,
            }}>
              Aralık gösteriyoruz: tüketimin faturadan tahmin ediliyor — dürüst rakam.
            </Text>
          </LinearGradient>

          {/* Grafik */}
          <View style={kart}>
            <Text style={[yazi.etiket, { marginBottom: bosluk.s }]}>24 saatlik görünüm</Text>
            <GunlukGrafik
              uretim={plan.ozet_veri.uretim}
              tuketim={plan.ozet_veri.tuketim}
              dilim={plan.ozet_veri.dilim}
            />
          </View>

          {/* Plan kalemleri */}
          {plan.kalemler.length > 0 && (
            <Text style={[yazi.etiket, { marginBottom: bosluk.s, marginLeft: 2 }]}>
              Günün planı
            </Text>
          )}
          {plan.kalemler.length === 0 ? (
            <View style={kart}>
              <Text style={yazi.govde}>
                Planlanacak esnek cihaz yok. Ayarlar'dan çamaşır makinesi gibi cihazlar ekle —
                Voltaic onları en ucuz saate yerleştirsin.
              </Text>
            </View>
          ) : (
            plan.kalemler.map((kalem, i) => (
              <PlanKarti key={i} kalem={kalem} kullaniciId={kullaniciId} tarih={plan.tarih} />
            ))
          )}

          {/* Proaktif uyarılar */}
          {bildirimler.map((uyari, i) => (
            <View
              key={i}
              style={[kart, {
                flexDirection: 'row', gap: 12,
                borderLeftWidth: 3, borderLeftColor: renk.amber,
              }]}
            >
              <View style={{
                width: 38, height: 38, borderRadius: 19, backgroundColor: renk.amberYumusak,
                alignItems: 'center', justifyContent: 'center',
              }}>
                <GunesIkon boyut={20} renk={renk.amber} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={yazi.altBaslik}>{uyari.baslik.replace(' ☀️', '')}</Text>
                <Text style={[yazi.govde, { marginTop: 3, fontSize: 13.5 }]}>{uyari.metin}</Text>
              </View>
            </View>
          ))}
        </>
      )}
    </ScrollView>
  );
}
