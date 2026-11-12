/**
 * Lecture des modules de la boutique active : `GET /shops/{id}/profile` → `enabled_modules`.
 * Gardés dans `localStorage` pour ouvrir la boutique **sans réseau** : la dernière valeur connue
 * s'affiche tout de suite, puis la réponse du serveur la remplace.
 */
import { useEffect, useState } from "react";
import { NetworkError } from "../api/errors";
import { useServices } from "../services/servicesContext";
import { shopModules, type ShopModules } from "./modules";

export const MODULES_KEY = "boutique.shop-modules";

export type ModulesState =
  | { status: "loading" }
  | { status: "ready"; modules: ShopModules }
  | { status: "offline" };

type Saved = Record<string, readonly string[]>;

function readSaved(): Saved {
  const text = window.localStorage.getItem(MODULES_KEY);
  if (text === null) return {};
  const value: unknown = JSON.parse(text);
  const valid =
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    Object.values(value).every(
      (codes) => Array.isArray(codes) && codes.every((code) => typeof code === "string"),
    );
  if (!valid) throw new Error(`Modules gardés mal formés dans « ${MODULES_KEY} »`);
  return value as Saved;
}

function save(shopId: string, codes: readonly string[]): void {
  window.localStorage.setItem(MODULES_KEY, JSON.stringify({ ...readSaved(), [shopId]: codes }));
}

function savedState(shopId: string): ModulesState {
  const codes = readSaved()[shopId];
  return codes === undefined ? { status: "loading" } : { status: "ready", modules: shopModules(codes) };
}

/** Modules de `shopId` ; `retry` relit le serveur (après « Connexion nécessaire »). */
export function useShopModules(shopId: string): { state: ModulesState; retry: () => void } {
  const { api, session } = useServices();
  const [round, setRound] = useState(0);
  const [loaded, setLoaded] = useState<{ shopId: string; state: ModulesState } | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  if (failure !== null) throw failure instanceof Error ? failure : new Error(String(failure));

  useEffect(() => {
    let current = true;
    session
      .authorized((token) =>
        api.get("/api/v1/shops/{shop_id}/profile", { token, params: { shop_id: shopId } }),
      )
      .then(
        (profile) => {
          if (!current) return;
          const modules = shopModules(profile.enabled_modules);
          save(shopId, profile.enabled_modules);
          setLoaded({ shopId, state: { status: "ready", modules } });
        },
        (error: unknown) => {
          if (!current) return;
          if (!(error instanceof NetworkError)) {
            setFailure(error);
            return;
          }
          const saved = savedState(shopId);
          setLoaded({ shopId, state: saved.status === "ready" ? saved : { status: "offline" } });
        },
      );
    return () => {
      current = false;
    };
  }, [api, session, shopId, round]);

  const state = loaded?.shopId === shopId ? loaded.state : savedState(shopId);
  return {
    state,
    retry: () => {
      setLoaded(null);
      setRound((n) => n + 1);
    },
  };
}
