import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useI18n } from '@/shared/i18n';
import { useTheme } from '@/shared/theme/use-theme';
import { setAccessToken, setAccessTokenRefresher, setSessionExpiredHandler } from '@/shared/api';
import { queryClient } from '@/shared/query/query-client';
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
import { patchSessionProfile, type SessionProfilePatch } from './session-profile';
import { isSessionSyncMessage, sessionSyncChannelName, type SessionSyncMessage } from './session-sync';

type SessionOperation = {
  controller: AbortController;
  id: number;
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const { setLocale } = useI18n();
  const { setMode } = useTheme();
  const [profile, setProfileState] = useState<CurrentUserProfile | null>(null);
  const [status, setStatus] = useState<AuthStatus>('checking');
  const [loading, setLoading] = useState(false);
  const operationIdRef = useRef(0);
  const activeOperationRef = useRef<SessionOperation | null>(null);
  const sessionChannelRef = useRef<BroadcastChannel | null>(null);

  const broadcastSessionEvent = useCallback((message: SessionSyncMessage) => {
    sessionChannelRef.current?.postMessage(message);
  }, []);

  const beginOperation = useCallback(() => {
    activeOperationRef.current?.controller.abort();
    const operation = {
      controller: new AbortController(),
      id: operationIdRef.current + 1,
    };
    operationIdRef.current = operation.id;
    activeOperationRef.current = operation;
    setLoading(true);
    return operation;
  }, []);

  const isCurrentOperation = useCallback(
    (operation: SessionOperation) => activeOperationRef.current === operation && !operation.controller.signal.aborted,
    [],
  );

  const finishOperation = useCallback((operation: SessionOperation) => {
    if (activeOperationRef.current !== operation) {
      return;
    }

    activeOperationRef.current = null;
    setLoading(false);
  }, []);

  const resetSessionState = useCallback((nextStatus: Exclude<AuthStatus, 'authenticated'>) => {
    setAccessToken(null);
    queryClient.clear();
    setProfileState(null);
    setStatus(nextStatus);
  }, []);

  const clearSessionState = useCallback(() => {
    resetSessionState('anonymous');
  }, [resetSessionState]);

  const prepareSessionCheck = useCallback(() => {
    resetSessionState('checking');
  }, [resetSessionState]);

  const clearSession = useCallback(() => {
    activeOperationRef.current?.controller.abort();
    activeOperationRef.current = null;
    clearSessionState();
    setLoading(false);
  }, [clearSessionState]);

  const expireSession = useCallback(() => {
    clearSession();
    broadcastSessionEvent({ type: 'logout' });
  }, [broadcastSessionEvent, clearSession]);

  const completeAuthenticatedSession = useCallback(
    async (access: string, operation: SessionOperation) => {
      if (!access.trim()) {
        throw new Error('Authentication returned an empty access token');
      }
      if (!isCurrentOperation(operation)) {
        return;
      }

      setAccessToken(access);
      const nextProfile = await fetchCurrentUserProfile({ signal: operation.controller.signal });
      if (!isCurrentOperation(operation)) {
        return;
      }

      setProfileState(nextProfile);
      setStatus('authenticated');
    },
    [isCurrentOperation],
  );

  const patchProfile = useCallback((patch: SessionProfilePatch) => {
    setProfileState((currentProfile) => patchSessionProfile(currentProfile, patch));
  }, []);

  const authenticate = useCallback(
    async (requestAccessToken: (signal: AbortSignal) => Promise<string>) => {
      const operation = beginOperation();
      try {
        const access = await requestAccessToken(operation.controller.signal);
        await completeAuthenticatedSession(access, operation);
      } catch (error) {
        if (isCurrentOperation(operation)) {
          clearSessionState();
        }
        throw error;
      } finally {
        finishOperation(operation);
      }
    },
    [beginOperation, clearSessionState, completeAuthenticatedSession, finishOperation, isCurrentOperation],
  );

  const refreshSession = useCallback(async () => {
    await authenticate((signal) => refreshAccessToken({ signal }));
  }, [authenticate]);

  const loginWithPassword = useCallback(
    async (input: PasswordLoginInput) => {
      clearSessionState();
      await authenticate(async (signal) => (await requestPasswordLogin(input, { signal })).access);
      broadcastSessionEvent({ type: 'authenticated' });
    },
    [authenticate, broadcastSessionEvent, clearSessionState],
  );

  const loginWithCode = useCallback(
    async (input: CodeLoginInput) => {
      clearSessionState();
      await authenticate(async (signal) => (await requestCodeLogin(input, { signal })).access);
      broadcastSessionEvent({ type: 'authenticated' });
    },
    [authenticate, broadcastSessionEvent, clearSessionState],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      clearSessionState();
      await authenticate(async (signal) => (await registerAccount(input, { signal })).access);
      broadcastSessionEvent({ type: 'authenticated' });
    },
    [authenticate, broadcastSessionEvent, clearSessionState],
  );

  const logout = useCallback(async () => {
    const operation = beginOperation();
    clearSessionState();
    try {
      await logoutSession({ signal: operation.controller.signal });
      broadcastSessionEvent({ type: 'logout' });
    } finally {
      finishOperation(operation);
    }
  }, [beginOperation, broadcastSessionEvent, clearSessionState, finishOperation]);

  useEffect(() => {
    if (!profile) return;

    setMode(profile.appearance ?? 'auto');
    if (profile.language) setLocale(profile.language);
  }, [profile, setLocale, setMode]);

  useEffect(() => {
    if (typeof BroadcastChannel === 'undefined') return;

    let channel: BroadcastChannel;
    try {
      channel = new BroadcastChannel(sessionSyncChannelName);
    } catch {
      return;
    }

    sessionChannelRef.current = channel;
    channel.onmessage = (event: MessageEvent<unknown>) => {
      if (!isSessionSyncMessage(event.data)) return;
      if (event.data.type === 'logout') {
        clearSession();
        return;
      }
      prepareSessionCheck();
      void refreshSession().catch(() => {
        clearSession();
      });
    };

    return () => {
      if (sessionChannelRef.current === channel) sessionChannelRef.current = null;
      channel.close();
    };
  }, [clearSession, prepareSessionCheck, refreshSession]);

  useEffect(() => {
    setAccessTokenRefresher(refreshAccessToken);
    setSessionExpiredHandler(expireSession);

    return () => {
      setAccessTokenRefresher(null);
      setSessionExpiredHandler(null);
      setAccessToken(null);
    };
  }, [expireSession]);

  useEffect(() => {
    void authenticate((signal) => refreshAccessToken({ signal })).catch(() => undefined);

    return () => {
      activeOperationRef.current?.controller.abort();
      activeOperationRef.current = null;
    };
  }, [authenticate]);

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
      patchProfile,
    }),
    [loading, loginWithCode, loginWithPassword, logout, patchProfile, profile, register, status],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
