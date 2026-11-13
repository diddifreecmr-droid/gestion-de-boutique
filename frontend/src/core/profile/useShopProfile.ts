/**
 * Lecture du profil de la boutique active : `GET /shops/{id}/profile` (menus, libellés, rôles,
 * champs, `enabled_modules`). Gardé dans `localStorage` pour ouvrir la boutique **sans réseau** :
 * la dernière valeur connue s'affiche tout de suite, puis la réponse du serveur la remplace.
 * Hors connexion et sans valeur gardée, rien n'est inventé (`unavailable`) : la lecture est
 * refaite au retour du réseau.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import type { Role } from "../auth/me";
import { NetworkError } from "../api/errors";
import { useIsOnline, useServices } from "../services/servicesContext";
import { shopModules, type ShopModules } from "./modules";
import { saveProfile, savedProfile } from "./savedProfiles";
import { profileFromResponse, type ProfileResponse } from "./servedProfile";
import { withModules } from "./shopProfile";
import type { ShopProfile } from "./types";

export type ShopProfileState =
  | { status: "loading" }
  | { status: "unavailable" }
  | { status: "ready"; profile: ShopProfile; modules: ShopModules };

interface Loaded {
  shopId: string;
  /** `null` : coupure sans profil gardé. */
  response: ProfileResponse | null;
  /** Vrai si la valeur ne vient pas du serveur (coupure) : à relire au retour du réseau. */
  fallback: boolean;
}

function stateOf(response: ProfileResponse | null, role: Role): ShopProfileState {
  if (response === null) return { status: "unavailable" };
  const modules = shopModules(response.enabled_modules);
  const profile = withModules(profileFromResponse(response, role), modules);
  return { status: "ready", profile, modules };
}

/** Profil de `shopId` pour `role`, relu au retour du réseau tant que le serveur n'a pas répondu. */
export function useShopProfile(shopId: string, role: Role): ShopProfileState {
  const { api, session } = useServices();
  const online = useIsOnline();
  // Dernier profil gardé : affiché tout de suite, puis remplacé par la réponse du serveur.
  const [loaded, setLoaded] = useState<Loaded | null>(() => {
    const saved = savedProfile(shopId, role);
    return saved === null ? null : { shopId, response: saved, fallback: true };
  });
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
        (response) => {
          if (!current) return;
          profileFromResponse(response, role); // contrôle avant de garder (fail-fast)
          saveProfile(shopId, response);
          keep({ shopId, response, fallback: false });
        },
        (error: unknown) => {
          if (!current) return;
          if (!(error instanceof NetworkError)) {
            setFailure(error);
            return;
          }
          keep({ shopId, response: savedProfile(shopId, role), fallback: true });
        },
      )
      .catch((error: unknown) => {
        if (current) setFailure(error);
      });
    return () => {
      current = false;
    };
  }, [api, session, shopId, role, online]);

  // Une seule construction par réponse : la valeur des modules et du profil reste stable d'un
  // rendu à l'autre (les écrans s'en servent dans leurs dépendances d'effets).
  const shown = loaded?.shopId === shopId ? loaded : null;
  return useMemo<ShopProfileState>(
    () => (shown === null ? { status: "loading" } : stateOf(shown.response, role)),
    [shown, role],
  );
}
