/// <reference types="vite/client" />

interface ViteTypeOptions {
  strictImportMetaEnv: unknown;
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_HCAPTCHA_SITE_KEY?: string;
  readonly VITE_SITE_URL?: string;
}
