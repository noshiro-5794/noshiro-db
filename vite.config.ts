import { defineConfig, loadEnv } from 'vite';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

const defaultApiProxyTarget = 'https://api.noshiro.moe';

function readApiProxyTarget(value: string | undefined) {
  const url = new URL(value?.trim() || defaultApiProxyTarget);

  if (!['http:', 'https:'].includes(url.protocol) || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('API_PROXY_TARGET must be an HTTP(S) origin without a path, query, or fragment');
  }

  return url.origin;
}

function allowRefreshCookieOnHttpDevelopmentOrigin(header: string) {
  return header
    .split(';')
    .filter((part) => part.trim().toLowerCase() !== 'secure')
    .join(';');
}

export default defineConfig(({ mode }) => {
  const configEnv = loadEnv(mode, process.cwd(), 'API_PROXY_TARGET');
  const apiProxyTarget = readApiProxyTarget(configEnv.API_PROXY_TARGET);

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
          cookieDomainRewrite: '',
          configure(proxy) {
            proxy.on('proxyRes', (proxyResponse) => {
              const setCookie = proxyResponse.headers['set-cookie'];
              if (!setCookie) return;

              // Vite serves HTTP by default. Browsers reject the production Secure cookie
              // on LAN, IPv6, and custom development hosts even though the proxy is same-origin.
              proxyResponse.headers['set-cookie'] = setCookie.map(allowRefreshCookieOnHttpDevelopmentOrigin);
            });
          },
          ...(apiProxyTarget === defaultApiProxyTarget
            ? {
                headers: {
                  Origin: 'https://app.noshiro.moe',
                },
              }
            : {}),
          secure: true,
        },
      },
    },
  };
});
