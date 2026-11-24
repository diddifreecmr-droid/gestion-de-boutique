import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ShopLogoState } from "../core/profile/shopLogoContext";
import { useServices } from "../core/services/servicesContext";

/**
 * Logo affiché par la coquille : celui du profil (chemin servi → adresse de l'API), sauf s'il a
 * été remplacé sur place (envoi : aperçu local `blob:` ; retrait : `null`). Un aperçu local
 * remplacé ou abandonné est libéré (`URL.revokeObjectURL`).
 */
export function useShopLogoState(servedPath: string | null): ShopLogoState {
  const { api } = useServices();
  const [override, setOverride] = useState<{ src: string | null } | null>(null);
  const local = useRef<string | null>(null);

  const release = () => {
    if (local.current !== null) URL.revokeObjectURL(local.current);
    local.current = null;
  };
  useEffect(() => release, []);

  const replace = useCallback((src: string | null) => {
    release();
    if (src?.startsWith("blob:") === true) local.current = src;
    setOverride({ src });
  }, []);

  const served = servedPath === null ? null : api.href(servedPath);
  const src = override === null ? served : override.src;
  return useMemo(() => ({ src, replace }), [src, replace]);
}
