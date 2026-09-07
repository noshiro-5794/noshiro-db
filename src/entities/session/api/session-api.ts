import { api } from '@/shared/api';
import type {
  AccessTokenPayload,
  ApiRequestContext,
  CurrentUserProfile,
  ProfileStats,
  SendCodePurpose,
} from '@/shared/api';
import {
  decodeAccessTokenPayload,
  decodeAvatarUpload,
  decodeCurrentUserProfile,
  decodeProfileStats,
} from './session-decoders';

export const authApi = {
  sendCode: (
    body: { email: string; purpose: SendCodePurpose; hcaptcha_token?: string },
    context: ApiRequestContext = {},
  ) => api.post<unknown, typeof body>('/api/v1/auth/verification-codes/', body, { ...context, skipAuth: true }),

  register: (
    body: { email: string; password: string; nickname: string; code: string },
    context: ApiRequestContext = {},
  ) =>
    api.post<AccessTokenPayload, typeof body>('/api/v1/auth/registrations/', body, {
      ...context,
      decode: decodeAccessTokenPayload,
      skipAuth: true,
    }),

  loginWithPassword: (body: { email: string; password: string }, context: ApiRequestContext = {}) =>
    api.post<AccessTokenPayload, typeof body>('/api/v1/auth/sessions/password/', body, {
      ...context,
      decode: decodeAccessTokenPayload,
      skipAuth: true,
    }),

  loginWithCode: (body: { email: string; code: string }, context: ApiRequestContext = {}) =>
    api.post<AccessTokenPayload, typeof body>('/api/v1/auth/sessions/code/', body, {
      ...context,
      decode: decodeAccessTokenPayload,
      skipAuth: true,
    }),

  refreshToken: (context: ApiRequestContext = {}) =>
    api.post<AccessTokenPayload>('/api/v1/auth/sessions/refresh/', undefined, {
      ...context,
      decode: decodeAccessTokenPayload,
      skipAuth: true,
    }),

  logout: (context: ApiRequestContext = {}) => api.post<unknown>('/api/v1/auth/session/', undefined, context),

  resetPassword: (body: { email: string; code: string; new_password: string }) =>
    api.post<unknown, typeof body>('/api/v1/auth/password-resets/', body, { skipAuth: true }),
};

export const profileApi = {
  getMe: (context: ApiRequestContext = {}) =>
    api.get<CurrentUserProfile>('/api/v1/users/me/profile/', { ...context, decode: decodeCurrentUserProfile }),

  updateMe: (body: Partial<Pick<CurrentUserProfile, 'nickname' | 'bio'>>) =>
    api.patch<CurrentUserProfile, typeof body>('/api/v1/users/me/profile/', body, { decode: decodeCurrentUserProfile }),

  getSettings: (context: ApiRequestContext = {}) =>
    api.get<CurrentUserProfile>('/api/v1/users/me/settings/', { ...context, decode: decodeCurrentUserProfile }),

  updateSettings: (body: Partial<Pick<CurrentUserProfile, 'language' | 'appearance'>>) =>
    api.patch<CurrentUserProfile, typeof body>('/api/v1/users/me/settings/', body, {
      decode: decodeCurrentUserProfile,
    }),

  getStats: (query: { year?: number; timezone?: string } = {}, context: ApiRequestContext = {}) =>
    api.get<ProfileStats>('/api/v1/users/me/profile/stats/', { ...context, decode: decodeProfileStats, query }),

  uploadAvatar: (avatar: File) => {
    const body = new FormData();
    body.set('avatar', avatar);
    return api.post<{ avatar: string }, FormData>('/api/v1/users/me/avatar/', body, { decode: decodeAvatarUpload });
  },
};
