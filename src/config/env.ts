const stripTrailingSlash = (value: string) => value.replace(/\/+$/, '');

export const env = {
  apiBaseUrl: stripTrailingSlash(import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8008'),
  hcaptchaSiteKey: import.meta.env.VITE_HCAPTCHA_SITE_KEY ?? '',
};
