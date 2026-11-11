/**
 * Réglages de l'environnement E2E, lus une fois et validés (fail-fast).
 *
 * Les serveurs de développement (backend 8000, frontend 5173) ne sont jamais utilisés :
 * les ports E2E par défaut sont 8100 et 5273, et 8000 / 5173 sont refusés explicitement.
 */
const FORBIDDEN_PORTS = new Set([8000, 5173]);

function port(name: string, fallback: number): number {
  const raw = process.env[name];
  const value = raw === undefined || raw === "" ? fallback : Number(raw);
  if (!Number.isInteger(value) || value <= 0 || value > 65535) {
    throw new Error(`${name} invalide : « ${String(raw)} » (entier 1–65535 attendu)`);
  }
  if (FORBIDDEN_PORTS.has(value)) {
    throw new Error(`${name} = ${String(value)} : port réservé au développement, interdit en E2E`);
  }
  return value;
}

export const BACKEND_PORT = port("E2E_BACKEND_PORT", 8100);
export const FRONTEND_PORT = port("E2E_FRONTEND_PORT", 5273);

if (BACKEND_PORT === FRONTEND_PORT) {
  throw new Error(`E2E_BACKEND_PORT et E2E_FRONTEND_PORT identiques (${String(BACKEND_PORT)})`);
}

/** Exécutable `uv` : `UV_BIN` si fourni (chemin absolu sous Windows), sinon `uv` du PATH. */
export const UV_BIN = process.env["UV_BIN"]?.trim() || "uv";

export const API_PREFIX = "/api/v1";
export const FRONTEND_URL = `http://127.0.0.1:${String(FRONTEND_PORT)}`;
export const BACKEND_URL = `http://127.0.0.1:${String(BACKEND_PORT)}`;

/** Mot d'étiquette : tests propres au téléphone, exclus du projet ordinateur. */
export const MOBILE_ONLY = "@mobile-only";
