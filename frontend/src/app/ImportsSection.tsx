import { lazy, Suspense } from "react";
import type { Role } from "../core/auth/me";
import { useModules } from "../core/profile/modulesContext";
import { IMPORT_ROLES } from "../features/imports/importModels";
import { IMPORT_MODULE } from "../features/imports/importsNav";
import { Skeleton } from "../shared/ui";
import { NotFoundPage } from "./NotFoundPage";

/** Écran chargé à la demande (specs § 4.6). */
const ImportsRoute = lazy(() => import("../features/imports/ImportsRoute"));

/**
 * `/s/{id}/import` (propriétaire, comptable) : n'existe que si le module `import` de la
 * boutique est actif (specs § 15.1 : on ne montre jamais ce qui n'existe pas). Le module est
 * « à venir » jusqu'à T46 : l'écran reste introuvable pour toute boutique d'ici là.
 */
export function ImportsSection({ shopId, role }: { shopId: string; role: Role }) {
  const modules = useModules();
  if (!modules.has(IMPORT_MODULE) || !IMPORT_ROLES.includes(role)) return <NotFoundPage />;
  return (
    <Suspense fallback={<Skeleton lines={4} label="Ouverture de l'import…" />}>
      <ImportsRoute shopId={shopId} role={role} />
    </Suspense>
  );
}
