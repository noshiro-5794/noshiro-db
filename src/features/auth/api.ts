import { api } from '@/lib/api/client';
import type { AccessTokenPayload, CurrentUserProfile, ProfileStats, SendCodePurpose } from '@/lib/api/types';

export const authApi = {
  sendCode: (body: { email: string; purpose: SendCodePurpose; hcaptcha_token?: string }) =>
    api.post<unknown, typeof body>('/api/users/send-code/', body, { skipAuth: true }),

  register: (body: { email: string; password: string; nickname: string; code: string }) =>
    api.post<AccessTokenPayload, typeof body>('/api/users/register/', body, { skipAuth: true }),

  loginWithPassword: (body: { email: string; password: string }) =>
    api.post<AccessTokenPayload, typeof body>('/api/users/login/password/', body, { skipAuth: true }),

  loginWithCode: (body: { email: string; code: string }) =>
    api.post<AccessTokenPayload, typeof body>('/api/users/login/code/', body, { skipAuth: true }),

  refreshToken: () => api.post<AccessTokenPayload>('/api/users/token/refresh/', undefined, { skipAuth: true }),

  logout: () => api.post<unknown>('/api/users/logout/'),

  resetPassword: (body: { email: string; code: string; new_password: string }) =>
    api.post<unknown, typeof body>('/api/users/password/reset/', body, { skipAuth: true }),
};

export const profileApi = {
  getMe: () => api.get<CurrentUserProfile>('/api/users/me/profile/'),

  updateMe: (body: Partial<Pick<CurrentUserProfile, 'nickname' | 'bio' | 'theme_color'>>) =>
    api.patch<CurrentUserProfile, typeof body>('/api/users/me/profile/', body),

  getSettings: () => api.get<CurrentUserProfile>('/api/users/me/settings/'),

  updateSettings: (body: Partial<Pick<CurrentUserProfile, 'language' | 'appearance' | 'theme_color'>>) =>
    api.patch<CurrentUserProfile, typeof body>('/api/users/me/settings/', body),

  getStats: (query: { year?: number; timezone?: string } = {}) =>
    api.get<ProfileStats>('/api/users/me/profile/stats/', { query }),

  uploadAvatar: (avatar: File) => {
    const body = new FormData();
    body.set('avatar', avatar);
    return api.post<{ avatar: string }, FormData>('/api/users/me/avatar/', body);
  },
};
