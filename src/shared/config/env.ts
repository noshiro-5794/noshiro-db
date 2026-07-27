function readOrigin(name: string, value: string | undefined, fallback: string) {
  const candidate = value?.trim() || fallback;
  let url: URL;

  try {
    url = new URL(candidate);
  } catch {
    throw new Error(`${name} must be a valid absolute URL`);
  }

  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new Error(`${name} must use http or https`);
  }

  if (url.pathname !== '/' || url.search || url.hash || url.username || url.password) {
    throw new Error(`${name} must be an origin without a path, query, credentials, or fragment`);
  }

  return url.origin;
}

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL?.trim()
    ? readOrigin('VITE_API_BASE_URL', import.meta.env.VITE_API_BASE_URL, 'https://api.noshiro.moe')
    : import.meta.env.DEV
      ? ''
      : 'https://api.noshiro.moe',
  siteUrl: readOrigin('VITE_SITE_URL', import.meta.env.VITE_SITE_URL, 'https://noshiro.moe'),
  hcaptchaSiteKey: import.meta.env.VITE_HCAPTCHA_SITE_KEY?.trim() ?? '',
};
