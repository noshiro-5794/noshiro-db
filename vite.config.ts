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
          ...(apiProxyTarget === defaultApiProxyTarget
            ? {
                headers: {
                  Origin: 'https://noshiro.moe',
                },
              }
            : {}),
          secure: true,
        },
      },
    },
  };
});
