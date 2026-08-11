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
  ) => api.post<unknown, typeof body>('/api/users/send-code/', body, { ...context, skipAuth: true }),

  register: (
    body: { email: string; password: string; nickname: string; code: string },
    context: ApiRequestContext = {},
  ) =>
    api.post<AccessTokenPayload, typeof body>('/api/users/register/', body, {
      ...context,
      decode: decodeAccessTokenPayload,
      skipAuth: true,
    }),

  loginWithPassword: (body: { email: string; password: string }, context: ApiRequestContext = {}) =>
    api.post<AccessTokenPayload, typeof body>('/api/users/login/password/', body, {
      ...context,
      decode: decodeAccessTokenPayload,
      skipAuth: true,
    }),

  loginWithCode: (body: { email: string; code: string }, context: ApiRequestContext = {}) =>
    api.post<AccessTokenPayload, typeof body>('/api/users/login/code/', body, {
      ...context,
      decode: decodeAccessTokenPayload,
      skipAuth: true,
    }),

  refreshToken: (context: ApiRequestContext = {}) =>
    api.post<AccessTokenPayload>('/api/users/token/refresh/', undefined, {
      ...context,
      decode: decodeAccessTokenPayload,
      skipAuth: true,
    }),

  logout: (context: ApiRequestContext = {}) => api.post<unknown>('/api/users/logout/', undefined, context),

  resetPassword: (body: { email: string; code: string; new_password: string }) =>
    api.post<unknown, typeof body>('/api/users/password/reset/', body, { skipAuth: true }),
};

export const profileApi = {
  getMe: (context: ApiRequestContext = {}) =>
    api.get<CurrentUserProfile>('/api/users/me/profile/', { ...context, decode: decodeCurrentUserProfile }),

  updateMe: (body: Partial<Pick<CurrentUserProfile, 'nickname' | 'bio'>>) =>
    api.patch<CurrentUserProfile, typeof body>('/api/users/me/profile/', body, { decode: decodeCurrentUserProfile }),

  getSettings: (context: ApiRequestContext = {}) =>
    api.get<CurrentUserProfile>('/api/users/me/settings/', { ...context, decode: decodeCurrentUserProfile }),

  updateSettings: (body: Partial<Pick<CurrentUserProfile, 'language' | 'appearance'>>) =>
    api.patch<CurrentUserProfile, typeof body>('/api/users/me/settings/', body, { decode: decodeCurrentUserProfile }),

  getStats: (query: { year?: number; timezone?: string } = {}, context: ApiRequestContext = {}) =>
    api.get<ProfileStats>('/api/users/me/profile/stats/', { ...context, decode: decodeProfileStats, query }),

  uploadAvatar: (avatar: File) => {
    const body = new FormData();
    body.set('avatar', avatar);
    return api.post<{ avatar: string }, FormData>('/api/users/me/avatar/', body, { decode: decodeAvatarUpload });
  },
};
