/**
 * Configuration Vite des tests E2E : celle du frontend, inchangée, sauf le serveur.
 *
 * `frontend/vite.config.ts` fixe le proxy `/api` sur 127.0.0.1:8000 (backend de développement)
 * sans variable pour le surcharger. On ne modifie pas `frontend/` : on réutilise sa configuration
 * et on remplace seulement `server` (port E2E, proxy vers le backend jetable).
 *
 * Variables lues (posées par `playwright.config.ts`) : E2E_FRONTEND_PORT, E2E_BACKEND_PORT.
 */
import { fileURLToPath } from "node:url";
import frontendConfig from "../../frontend/vite.config.ts";

function requiredPort(name) {
  const raw = process.env[name];
  const port = Number(raw);
  if (raw === undefined || !Number.isInteger(port) || port <= 0 || port > 65535) {
    throw new Error(`${name} absent ou invalide (« ${String(raw)} ») : lancer via Playwright`);
  }
  return port;
}

const frontendPort = requiredPort("E2E_FRONTEND_PORT");
const backendPort = requiredPort("E2E_BACKEND_PORT");

export default {
  ...frontendConfig,
  root: fileURLToPath(new URL("../../frontend/", import.meta.url)),
  // Cache de pré-bundling séparé : ne touche pas celui du serveur de développement.
  cacheDir: fileURLToPath(new URL("../node_modules/.vite-e2e/", import.meta.url)),
  clearScreen: false,
  server: {
    host: "127.0.0.1",
    port: frontendPort,
    strictPort: true,
    proxy: { "/api": `http://127.0.0.1:${String(backendPort)}` },
  },
};
