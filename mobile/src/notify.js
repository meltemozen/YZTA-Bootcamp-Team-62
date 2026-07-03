// Cross-platform alert/confirm.
// React Native's Alert is NOT IMPLEMENTED on web (silently does nothing);
// on web the browser's alert/confirm is used.

import { Alert, Platform } from 'react-native';

export function alertUser(title, message) {
  if (Platform.OS === 'web') {
    window.alert(message ? `${title}\n\n${message}` : title);
  } else {
    Alert.alert(title, message);
  }
}

export function confirmAction(title, message, confirmLabel, onConfirm) {
  if (Platform.OS === 'web') {
    if (window.confirm(`${title}\n\n${message}`)) onConfirm();
  } else {
    Alert.alert(title, message, [
      { text: 'Vazgeç', style: 'cancel' },
      { text: confirmLabel, style: 'destructive', onPress: onConfirm },
    ]);
  }
}
