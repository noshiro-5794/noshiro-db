const stripTrailingSlash = (value: string) => value.replace(/\/+$/, '');

export const env = {
  apiBaseUrl: stripTrailingSlash(import.meta.env.VITE_API_BASE_URL ?? 'https://api.noshiro.moe'),
  siteUrl: stripTrailingSlash(import.meta.env.VITE_SITE_URL ?? 'https://noshiro.moe'),
  hcaptchaSiteKey: import.meta.env.VITE_HCAPTCHA_SITE_KEY ?? '',
};
