// Single plan-item card: icon badge, hour, saving range, reason and an
// "Applied" toggle (the raw data for the counterfactual report comes from here).

import React, { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { api, rangeTL, REASON_TEXT } from '../api';
import { BatteryIcon, BoltIcon, PlugIcon } from './Icons';
import { card, colors, font, text } from '../theme';

const TYPE_ICON = { device: PlugIcon, battery_charge: BatteryIcon, battery_discharge: BoltIcon };

export default function PlanCard({ item, userId, date }) {
  const [applied, setApplied] = useState(false);
  const [saving, setSaving] = useState(false);

  const toggle = async () => {
    const next = !applied;
    setApplied(next);
    setSaving(true);
    try {
      await api.feedback({
        user_id: userId,
        date,
        item_name: item.name,
        applied: next,
      });
    } catch {
      setApplied(!next); // could not save, revert
    } finally {
      setSaving(false);
    }
  };

  const hours = `${String(item.start_h).padStart(2, '0')}:00–${String(
    item.end_h
  ).padStart(2, '0')}:00`;
  const title =
    item.type === 'battery_charge'
      ? 'Bataryayı güneşten doldur'
      : item.type === 'battery_discharge'
      ? 'Bataryayı kullan'
      : `${item.name} çalıştır`;
  const Icon = TYPE_ICON[item.type] || PlugIcon;

  return (
    <View style={card}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <View style={{
          width: 42, height: 42, borderRadius: 21, backgroundColor: colors.amberSoft,
          alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={21} color={colors.amber} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={text.subtitle}>{title}</Text>
          <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 8, marginTop: 3 }}>
            <Text style={{ fontFamily: font.number, fontSize: 15, color: colors.amber }}>
              {hours}
            </Text>
            {item.saving_tl_max > 0 && (
              <Text style={{ fontFamily: font.medium, fontSize: 13, color: colors.inkSecondary }}>
                {rangeTL(item.saving_tl_min, item.saving_tl_max)}
              </Text>
            )}
          </View>
          <Text style={[text.small, { marginTop: 3 }]}>
            {REASON_TEXT[item.reason_code] || ''}
          </Text>
        </View>
        {item.type !== 'battery_charge' && (
          <Pressable
            onPress={toggle}
            disabled={saving}
            style={{
              paddingVertical: 7, paddingHorizontal: 13, borderRadius: 18,
              borderWidth: 1,
              borderColor: applied ? colors.good : colors.border,
              backgroundColor: applied ? colors.goodBg : 'transparent',
            }}
          >
            <Text style={{
              fontSize: 12, fontFamily: font.semibold,
              color: applied ? colors.goodText : colors.inkSecondary,
            }}>
              {applied ? '✓ Uygulandı' : 'Uyguladım'}
            </Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}
