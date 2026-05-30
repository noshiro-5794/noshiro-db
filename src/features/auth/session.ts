import { authApi, profileApi } from '@/features/auth/api';
import type { CurrentUserProfile } from '@/lib/api/types';

export type { CurrentUserProfile };
export type PasswordLoginInput = { email: string; password: string };
export type CodeLoginInput = { email: string; code: string };
export type RegisterInput = { email: string; password: string; nickname: string; code: string };

export async function refreshAccessToken() {
  const payload = await authApi.refreshToken();
  return payload.access;
}

export async function loginWithPassword(input: PasswordLoginInput) {
  return authApi.loginWithPassword(input);
}

export async function loginWithCode(input: CodeLoginInput) {
  return authApi.loginWithCode(input);
}

export async function registerAccount(input: RegisterInput) {
  return authApi.register(input);
}

export async function logoutSession() {
  return authApi.logout();
}

export async function fetchCurrentUserProfile() {
  return profileApi.getMe();
}
