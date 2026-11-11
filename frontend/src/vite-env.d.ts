/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Préfixe de l'API (même origine, proxy `/api` : specs.md D11). */
  readonly VITE_API_BASE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

/** Version de l'application, injectée au build (vite.config.ts → config/version.ts). */
declare const __APP_VERSION__: string;
