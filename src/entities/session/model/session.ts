import { authApi, profileApi } from '../api/session-api';
import type { ApiRequestContext, CurrentUserProfile } from '@/shared/api';
import { withSessionCookieLock } from './session-cookie-lock';

export type { CurrentUserProfile };
export type PasswordLoginInput = { email: string; password: string };
export type CodeLoginInput = { email: string; code: string };
export type RegisterInput = { email: string; password: string; nickname: string; code: string };

let pendingRefresh: Promise<string> | null = null;

export function refreshAccessToken(context: ApiRequestContext = {}) {
  context.signal?.throwIfAborted();

  pendingRefresh ??= withSessionCookieLock(async () => {
    // A rotated refresh cookie must finish even if React replays the mounting effect.
    const payload = await authApi.refreshToken();
    return payload.access;
  }).finally(() => {
    pendingRefresh = null;
  });

  return pendingRefresh;
}

export async function loginWithPassword(input: PasswordLoginInput, context: ApiRequestContext = {}) {
  return withSessionCookieLock(() => authApi.loginWithPassword(input, context), context.signal);
}

export async function loginWithCode(input: CodeLoginInput, context: ApiRequestContext = {}) {
  return withSessionCookieLock(() => authApi.loginWithCode(input, context), context.signal);
}

export async function registerAccount(input: RegisterInput, context: ApiRequestContext = {}) {
  return withSessionCookieLock(() => authApi.register(input, context), context.signal);
}

export async function logoutSession(context: ApiRequestContext = {}) {
  return withSessionCookieLock(() => authApi.logout(context), context.signal);
}

export async function fetchCurrentUserProfile(context: ApiRequestContext = {}) {
  return profileApi.getMe(context);
}
