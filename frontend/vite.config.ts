import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";
import { VitePWA } from "vite-plugin-pwa";
import { readTokenFromFile } from "./config/tokens";
import { appVersion } from "./config/version";

/** Couleurs lues dans tokens.css : aucune couleur recopiée dans la configuration. */
const PRIMARY = readTokenFromFile("--color-primary");
const BACKGROUND = readTokenFromFile("--color-bg");

/** Remplace %THEME_COLOR% dans index.html ; échoue si le marqueur a disparu. */
function themeColorHtml(): Plugin {
  return {
    name: "theme-color-html",
    transformIndexHtml(html) {
      if (!html.includes("%THEME_COLOR%")) {
        throw new Error("index.html : marqueur %THEME_COLOR% introuvable");
      }
      return html.replaceAll("%THEME_COLOR%", PRIMARY);
    },
  };
}

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    themeColorHtml(),
    VitePWA({
      // Service worker écrit à la main (src/sw.ts) : précache seulement pour T03.
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.ts",
      // « prompt » : la nouvelle version attend la fermeture des onglets ou l'appui sur
      // « Mettre à jour » (specs.md § 7.3). Jamais de rechargement forcé.
      registerType: "prompt",
      // Inscription faite par l'application (src/core/pwa/updates.ts) : elle surveille aussi
      // les nouvelles versions (à l'ouverture puis toutes les 30 min).
      injectRegister: false,
      includeAssets: ["icons/icon.svg"],
      manifest: {
        name: "Gestion de boutique",
        short_name: "Boutique",
        description: "Stock, ventes, crédits et dépenses de la boutique.",
        lang: "fr",
        dir: "ltr",
        start_url: "/",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        theme_color: PRIMARY,
        background_color: BACKGROUND,
        // Icônes PROVISOIRES générées par scripts/generate-icons.mjs (à remplacer par le logo).
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      injectManifest: {
        globPatterns: ["**/*.{js,css,html,svg,png,webmanifest}"],
        // File hors connexion (Dexie, T23) : hors précache. Elle n'est téléchargée que si le
        // droit `offline_capture` est actif, puis gardée par le cache d'exécution (cache d'abord).
        globIgnores: ["**/assets/engine-*.js"],
      },
      devOptions: { enabled: false },
    }),
  ],
  define: {
    // Numéro de version affiché dans l'application (Réglages, Mon compte).
    __APP_VERSION__: JSON.stringify(appVersion()),
  },
  server: {
    // En développement, /api est relayé vers le backend local (même origine, D11) ; port de
    // backend/README.md. 127.0.0.1 et non localhost : uvicorn n'écoute pas en IPv6 (::1).
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: {
    sourcemap: false,
  },
});
