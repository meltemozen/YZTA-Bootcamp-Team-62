// AuthContext — global authentication state for the Wattra app.
// Provides user info (id, email, name, token status) and auth actions
// (login, register, logout, refreshToken) to all screens.

import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import {
  api, saveTokens, clearTokens, getAccessToken, getRefreshToken, setOnAuthExpired,
} from './api';

const AuthContext = createContext(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);       // { id, email, name }
  const [loading, setLoading] = useState(true);  // true while restoring session
  const [needsOnboarding, setNeedsOnboarding] = useState(false);

  // --- Restore session on app launch ---
  useEffect(() => {
    (async () => {
      try {
        const token = await getAccessToken();
        if (!token) { setLoading(false); return; }

        // Validate token by calling /api/auth/me
        const me = await api.authMe();
        const hasProfile = me.profile && me.profile.panel_kw > 0;
        setUser({ id: me.user_id, email: me.email, name: me.name, isAdmin: !!me.is_admin });
        setNeedsOnboarding(!hasProfile);
      } catch {
        // Token expired or invalid — clear and show login
        await clearTokens();
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // --- Wire up the 401 callback so api.js can trigger logout ---
  useEffect(() => {
    setOnAuthExpired(() => {
      logout();
    });
    return () => setOnAuthExpired(null);
  }, []);

  // --- Auth actions ---

  const login = async (email, password) => {
    const resp = await api.authLogin(email, password);
    await saveTokens(resp.access_token, resp.refresh_token);
    const me = await api.authMe();
    await AsyncStorage.setItem('userId', String(resp.user_id));
    await AsyncStorage.setItem('userName', me.name || '');
    await AsyncStorage.setItem('userEmail', me.email || email);
    setUser({
      id: me.user_id, email: me.email || email, name: me.name, isAdmin: !!me.is_admin,
    });
    setNeedsOnboarding(!me.profile);
    return resp;
  };

  const register = async (email, password, name) => {
    const resp = await api.authRegister(email, password, name);
    await saveTokens(resp.access_token, resp.refresh_token);
    await AsyncStorage.setItem('userId', String(resp.user_id));
    await AsyncStorage.setItem('userName', name);
    await AsyncStorage.setItem('userEmail', email);
    setUser({ id: resp.user_id, email, name, isAdmin: !!resp.is_admin });
    setNeedsOnboarding(true);
    return resp;
  };

  const logout = async () => {
    await clearTokens();
    setUser(null);
    setNeedsOnboarding(false);
  };

  const updateUser = (updates) => {
    setUser((prev) => (prev ? { ...prev, ...updates } : prev));
  };

  const completeOnboarding = () => {
    setNeedsOnboarding(false);
  };

  const value = useMemo(() => ({
    user,
    loading,
    needsOnboarding,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    updateUser,
    completeOnboarding,
  }), [user, loading, needsOnboarding]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
