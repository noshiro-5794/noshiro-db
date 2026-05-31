import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { setAccessToken, setAccessTokenRefresher, setSessionExpiredHandler } from '@/lib/api/client';
import {
  fetchCurrentUserProfile,
  loginWithCode as requestCodeLogin,
  loginWithPassword as requestPasswordLogin,
  logoutSession,
  refreshAccessToken,
  registerAccount,
  type CodeLoginInput,
  type CurrentUserProfile,
  type PasswordLoginInput,
  type RegisterInput,
} from './session';
import { AuthContext, type AuthState, type AuthStatus } from './auth-context-value';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<CurrentUserProfile | null>(null);
  const [status, setStatus] = useState<AuthStatus>('checking');
  const [loading, setLoading] = useState(false);

  const clearSession = useCallback(() => {
    setAccessToken(null);
    setProfile(null);
    setStatus('anonymous');
  }, []);

  const completeAuthenticatedSession = useCallback(async (access: string) => {
    setAccessToken(access);
    setProfile(await fetchCurrentUserProfile());
    setStatus('authenticated');
  }, []);

  const refreshSession = useCallback(async () => {
    setLoading(true);
    try {
      const access = await refreshAccessToken();
      await completeAuthenticatedSession(access);
    } catch (error) {
      clearSession();
      throw error;
    } finally {
      setLoading(false);
    }
  }, [clearSession, completeAuthenticatedSession]);

  const loginWithPassword = useCallback(
    async (input: PasswordLoginInput) => {
      setLoading(true);
      try {
        const { access } = await requestPasswordLogin(input);
        await completeAuthenticatedSession(access);
      } finally {
        setLoading(false);
      }
    },
    [completeAuthenticatedSession],
  );

  const loginWithCode = useCallback(
    async (input: CodeLoginInput) => {
      setLoading(true);
      try {
        const { access } = await requestCodeLogin(input);
        await completeAuthenticatedSession(access);
      } finally {
        setLoading(false);
      }
    },
    [completeAuthenticatedSession],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      setLoading(true);
      try {
        const { access } = await registerAccount(input);
        await completeAuthenticatedSession(access);
      } finally {
        setLoading(false);
      }
    },
    [completeAuthenticatedSession],
  );

  const logout = useCallback(async () => {
    setLoading(true);
    try {
      await logoutSession();
    } finally {
      clearSession();
      setLoading(false);
    }
  }, [clearSession]);

  useEffect(() => {
    setAccessTokenRefresher(refreshAccessToken);
    setSessionExpiredHandler(clearSession);

    return () => {
      setAccessTokenRefresher(null);
      setSessionExpiredHandler(null);
    };
  }, [clearSession]);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      setLoading(true);
      try {
        const access = await refreshAccessToken();
        if (cancelled) {
          return;
        }
        await completeAuthenticatedSession(access);
        if (cancelled) {
          return;
        }
      } catch {
        if (!cancelled) {
          clearSession();
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void restoreSession();

    return () => {
      cancelled = true;
    };
  }, [clearSession, completeAuthenticatedSession]);

  const value = useMemo<AuthState>(
    () => ({
      profile,
      status,
      role: profile?.is_staff || profile?.is_superuser ? 'admin' : profile ? 'user' : 'guest',
      loading,
      isAuthenticated: status === 'authenticated',
      loginWithPassword,
      loginWithCode,
      register,
      logout,
      refreshSession,
      clearSession,
    }),
    [clearSession, loading, loginWithCode, loginWithPassword, logout, profile, refreshSession, register, status],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
