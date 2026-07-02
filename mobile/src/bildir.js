// Platformlar arası uyarı/onay.
// React Native'in Alert'i web'de UYGULANMAMIŞTIR (sessizce hiçbir şey yapmaz);
// web'de tarayıcının alert/confirm'i kullanılır.

import { Alert, Platform } from 'react-native';

export function uyar(baslik, mesaj) {
  if (Platform.OS === 'web') {
    window.alert(mesaj ? `${baslik}\n\n${mesaj}` : baslik);
  } else {
    Alert.alert(baslik, mesaj);
  }
}

export function onayla(baslik, mesaj, onayMetni, geriCagri) {
  if (Platform.OS === 'web') {
    if (window.confirm(`${baslik}\n\n${mesaj}`)) geriCagri();
  } else {
    Alert.alert(baslik, mesaj, [
      { text: 'Vazgeç', style: 'cancel' },
      { text: onayMetni, style: 'destructive', onPress: geriCagri },
    ]);
  }
}
