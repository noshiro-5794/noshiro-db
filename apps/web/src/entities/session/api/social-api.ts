import { api } from '@/shared/api';

export type SocialProvider = {
  provider: string;
  enabled: boolean;
  authorizePath: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function decodeSocialProviders(value: unknown): SocialProvider[] {
  if (!Array.isArray(value)) {
    throw new TypeError('Invalid social provider list');
  }
  return value.map((entry) => {
    if (
      !isRecord(entry) ||
      typeof entry['provider'] !== 'string' ||
      typeof entry['enabled'] !== 'boolean' ||
      typeof entry['authorize_path'] !== 'string'
    ) {
      throw new TypeError('Invalid social provider entry');
    }
    return {
      provider: entry['provider'],
      enabled: entry['enabled'],
      authorizePath: entry['authorize_path'],
    };
  });
}

function decodeSocialAuthorizeUrl(value: unknown): string {
  if (!isRecord(value) || typeof value['authorize_url'] !== 'string' || !value['authorize_url']) {
    throw new TypeError('Invalid social authorize response');
  }
  return value['authorize_url'];
}

export const socialApi = {
  listProviders: () =>
    api.get<SocialProvider[]>('/api/v1/auth/social/providers/', {
      skipAuth: true,
      decode: decodeSocialProviders,
    }),

  // Returns the provider URL to navigate to; the browser carries the state.
  authorizeUrl: (provider: string, redirect: string) =>
    api.get<string>(`/api/v1/auth/social/${provider}/start/`, {
      query: { redirect },
      skipAuth: true,
      decode: decodeSocialAuthorizeUrl,
    }),
};
