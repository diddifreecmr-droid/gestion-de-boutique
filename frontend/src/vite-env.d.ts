/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Préfixe de l'API (même origine, proxy `/api` : specs.md D11). */
  readonly VITE_API_BASE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
