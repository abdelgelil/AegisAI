import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as authApi from './authApi';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore the session when the app opens
  useEffect(() => {
    let cancelled = false;
    authApi.getSession().then((session) => {
      if (!cancelled) {
        setUser(session ?? null);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const { user: next } = await authApi.login(email, password);
    setUser(next);
    return next;
  }, []);

  // Returns the new user. Only active accounts are signed in; pending ones are not.
  const signup = useCallback(async (details) => {
    const { user: next } = await authApi.signup(details);
    if (next.status === 'active') setUser(next);
    return next;
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, signup, logout }),
    [user, loading, login, signup, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
