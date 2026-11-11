/**
 * Playwright — recette Lot 1 (docs/recette-lot1.md § 5, specs.md § 12.1).
 *
 * Deux serveurs **jetables** démarrés pour la session et arrêtés à la fin :
 * - backend FastAPI sur 127.0.0.1:8100, `ENVIRONMENT=test`, persistance mémoire, secret JWT
 *   aléatoire tiré à chaque lancement (jamais écrit sur disque) ;
 * - frontend Vite sur 127.0.0.1:5273, configuration du frontend réutilisée avec un proxy
 *   `/api` vers 8100 (servers/vite.e2e.config.mjs).
 * Un serveur déjà présent sur ces ports fait échouer le lancement (aucune réutilisation).
 */
import { randomBytes } from "node:crypto";
import { defineConfig } from "@playwright/test";
import {
  API_PREFIX,
  BACKEND_PORT,
  BACKEND_URL,
  FRONTEND_PORT,
  FRONTEND_URL,
  MOBILE_ONLY,
  UV_BIN,
} from "./support/env";

const CI = Boolean(process.env["CI"]);

/** Secret de session des tests : 48 octets aléatoires, différent à chaque lancement. */
const jwtSecret = randomBytes(48).toString("base64url");

/** Contexte commun (recette § 5) : français, fuseau de Douala. */
const common = { browserName: "chromium", locale: "fr-FR", timezoneId: "Africa/Douala" } as const;

export default defineConfig({
  testDir: "./tests",
  outputDir: "./test-results",
  fullyParallel: true,
  forbidOnly: CI,
  retries: CI ? 1 : 0,
  ...(CI ? { workers: 2 } : {}),
  timeout: 30_000,
  expect: { timeout: 5_000 },
  reporter: [
    ["list"],
    ["html", { outputFolder: "./playwright-report", open: "never" }],
  ],
  use: {
    baseURL: FRONTEND_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      // Téléphone d'entrée de gamme (CDC § 21) : viewport de référence de la recette.
      name: "mobile-360",
      use: {
        ...common,
        viewport: { width: 360, height: 800 },
        deviceScaleFactor: 2,
        isMobile: true,
        hasTouch: true,
      },
    },
    {
      // Propriétaire sur ordinateur (focus clavier, A11Y-04).
      name: "desktop-1280",
      grepInvert: new RegExp(MOBILE_ONLY),
      use: { ...common, viewport: { width: 1280, height: 800 } },
    },
  ],
  webServer: [
    {
      name: "backend",
      command: `"${UV_BIN}" run --frozen uvicorn app.bootstrap.container:build_app --factory --host 127.0.0.1 --port ${String(BACKEND_PORT)} --log-level warning`,
      cwd: "../backend",
      url: `${BACKEND_URL}${API_PREFIX}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        ENVIRONMENT: "test",
        PERSISTENCE_BACKEND: "memory",
        JWT_SECRET: jwtSecret,
        API_PREFIX,
        // Explicite : un éventuel backend/.env local ne doit pas changer le comportement.
        AUTH_RATE_LIMIT_ENABLED: "false",
        LOG_LEVEL: "WARNING",
        PYTHONUTF8: "1",
      },
    },
    {
      name: "frontend",
      command: "node node_modules/vite/bin/vite.js --config ../e2e/servers/vite.e2e.config.mjs",
      cwd: "../frontend",
      url: `${FRONTEND_URL}/connexion`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        E2E_FRONTEND_PORT: String(FRONTEND_PORT),
        E2E_BACKEND_PORT: String(BACKEND_PORT),
        VITE_API_BASE: "/api",
      },
    },
  ],
});
