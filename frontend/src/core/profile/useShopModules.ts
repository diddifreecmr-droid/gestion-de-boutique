/**
 * Lecture des modules de la boutique active : `GET /shops/{id}/profile` → `enabled_modules`.
 * Gardés dans `localStorage` pour ouvrir la boutique **sans réseau** : la dernière valeur connue
 * s'affiche tout de suite, puis la réponse du serveur la remplace. Hors connexion et sans valeur
 * gardée, seuls les modules toujours actifs sont montrés (jamais un module peut-être éteint) ;
 * la lecture est refaite au retour du réseau.
 */
import { useEffect, useRef, useState } from "react";
import { NetworkError } from "../api/errors";
import { useIsOnline, useServices } from "../services/servicesContext";
import { shopModules, type ShopModules } from "./modules";

export const MODULES_KEY = "boutique.shop-modules";

export type ModulesState = { status: "loading" } | { status: "ready"; modules: ShopModules };

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

function savedModules(shopId: string): ShopModules | null {
  const codes = readSaved()[shopId];
  return codes === undefined ? null : shopModules(codes);
}

interface Loaded {
  shopId: string;
  modules: ShopModules;
  /** Vrai si la valeur ne vient pas du serveur (coupure) : à relire au retour du réseau. */
  fallback: boolean;
}

/** Modules de `shopId`, relus au retour du réseau tant que le serveur n'a pas répondu. */
export function useShopModules(shopId: string): ModulesState {
  const { api, session } = useServices();
  const online = useIsOnline();
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const last = useRef<Loaded | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  if (failure !== null) {
    throw failure instanceof Error
      ? failure
      : new Error(`Échec non standard : ${JSON.stringify(failure)}`);
  }

  useEffect(() => {
    const known = last.current;
    if (known?.shopId === shopId && !known.fallback) return; // déjà lu du serveur
    let current = true;
    const keep = (next: Loaded) => {
      last.current = next;
      setLoaded(next);
    };
    session
      .authorized((token) =>
        api.get("/api/v1/shops/{shop_id}/profile", { token, params: { shop_id: shopId } }),
      )
      .then(
        (profile) => {
          if (!current) return;
          const modules = shopModules(profile.enabled_modules);
          save(shopId, profile.enabled_modules);
          keep({ shopId, modules, fallback: false });
        },
        (error: unknown) => {
          if (!current) return;
          if (!(error instanceof NetworkError)) {
            setFailure(error);
            return;
          }
          keep({ shopId, modules: savedModules(shopId) ?? shopModules([]), fallback: true });
        },
      );
    return () => {
      current = false;
    };
  }, [api, session, shopId, online]);

  const modules = loaded?.shopId === shopId ? loaded.modules : savedModules(shopId);
  return modules === null ? { status: "loading" } : { status: "ready", modules };
}
