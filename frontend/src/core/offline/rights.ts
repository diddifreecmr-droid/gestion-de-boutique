/**
 * Droit `offline_capture` connu par boutique (TR-26). Le serveur l'expose dans
 * `GET /shops/{id}/profile` → `entitlements` ; chaque lecture du profil le note ici. Gardé dans
 * `localStorage` pour le connaître **sans réseau** à l'ouverture suivante. Seules les boutiques
 * ouvertes sont gardées : en V1 la clé reste absente (rien n'est jamais écrit).
 */
import { createStore, type Store } from "../state/store";

export const RIGHTS_KEY = "boutique.offline-rights";

type KeyValueStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export interface OfflineRights {
  isEnabled: (shopId: string) => boolean;
  /** À appeler avec les `entitlements` de chaque `GET /profile` lu. */
  note: (shopId: string, entitlements: Readonly<Record<string, boolean>>) => void;
  enabledShops: () => readonly string[];
  subscribe: (listener: () => void) => () => void;
}

function parse(text: string | null): string[] {
  if (text === null) return [];
  const value: unknown = JSON.parse(text);
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
    throw new Error(`Droits hors connexion mal formés dans « ${RIGHTS_KEY} »`);
  }
  return value;
}

export function createOfflineRights(
  storage: () => KeyValueStorage = () => window.localStorage,
): OfflineRights {
  let store: Store<readonly string[]> | null = null;
  const current = (): Store<readonly string[]> =>
    (store ??= createStore<readonly string[]>(parse(storage().getItem(RIGHTS_KEY))));
  return {
    isEnabled: (shopId) => current().get().includes(shopId),
    note: (shopId, entitlements) => {
      const enabled = entitlements["offline_capture"];
      if (typeof enabled !== "boolean") {
        throw new Error("Profil de boutique sans le droit « offline_capture » (contrat T23)");
      }
      const shops = current().get();
      const has = shops.includes(shopId);
      if (has === enabled) return;
      const next = has ? shops.filter((id) => id !== shopId) : [...shops, shopId];
      if (next.length === 0) storage().removeItem(RIGHTS_KEY);
      else storage().setItem(RIGHTS_KEY, JSON.stringify(next));
      current().set(next);
    },
    enabledShops: () => current().get(),
    subscribe: (listener) => current().subscribe(listener),
  };
}
