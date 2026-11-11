/**
 * Identité de l'appareil (specs § 6.1 : `X-Device-Id` obligatoire ; § 8.1 : session par
 * appareil). L'identifiant est un UUIDv7 créé une fois puis gardé dans `localStorage`.
 */
import { isUuidV7, uuidV7 } from "./uuidv7";

export const DEVICE_ID_KEY = "boutique.device-id";

/** Stockage local illisible (navigation privée stricte, site bloqué) : l'API est inutilisable. */
export class DeviceIdError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "DeviceIdError";
  }
}

type KeyValueStorage = Pick<Storage, "getItem" | "setItem">;

function defaultStorage(): KeyValueStorage {
  return window.localStorage;
}

/** Lit l'identifiant de l'appareil, ou le crée ; lève `DeviceIdError` si le stockage échoue. */
export function readDeviceId(storage: () => KeyValueStorage = defaultStorage): string {
  let store: KeyValueStorage;
  let saved: string | null;
  try {
    store = storage();
    saved = store.getItem(DEVICE_ID_KEY);
  } catch (cause) {
    throw new DeviceIdError("Stockage de l'appareil inaccessible : identifiant illisible", {
      cause,
    });
  }
  if (saved !== null && isUuidV7(saved)) return saved;
  const created = uuidV7();
  try {
    store.setItem(DEVICE_ID_KEY, created);
  } catch (cause) {
    throw new DeviceIdError("Stockage de l'appareil inaccessible : identifiant non enregistré", {
      cause,
    });
  }
  return created;
}

const PLATFORMS: readonly [RegExp, string][] = [
  [/Android/i, "Android"],
  [/iPhone|iPad|iPod/i, "iPhone"],
  [/Windows/i, "Windows"],
  [/Mac OS X|Macintosh/i, "Mac"],
  [/Linux/i, "Linux"],
];
const BROWSERS: readonly [RegExp, string][] = [
  [/SamsungBrowser/i, "Samsung Internet"],
  [/Edg\//i, "Edge"],
  [/OPR\/|Opera/i, "Opera"],
  [/Firefox\//i, "Firefox"],
  [/Chrome\//i, "Chrome"],
  [/Safari\//i, "Safari"],
];

function pick(table: readonly [RegExp, string][], userAgent: string, fallback: string): string {
  return table.find(([pattern]) => pattern.test(userAgent))?.[1] ?? fallback;
}

/** Libellé lisible de l'appareil, montré au propriétaire dans la liste des sessions. */
export function deviceLabel(userAgent: string): string {
  return `${pick(PLATFORMS, userAgent, "Appareil")} — ${pick(BROWSERS, userAgent, "Navigateur")}`;
}
