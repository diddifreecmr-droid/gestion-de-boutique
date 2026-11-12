import { lazy, Suspense } from "react";
import { useDashboardModule } from "../features/dashboard/dashboardModule";
import { FiguresPending } from "../features/dashboard/FiguresOffline";
import { Skeleton } from "../shared/ui";
import { NotFoundPage } from "./NotFoundPage";

/** Écran chargé à la demande (specs § 4.6). */
const DashboardRoute = lazy(() => import("../features/dashboard/DashboardRoute"));

export const DASHBOARD_OFFLINE = "Connexion nécessaire pour ouvrir le tableau de bord.";

/**
 * `/s/{id}/tableau-de-bord` (propriétaire) : n'existe que si le module `dashboard` de la
 * boutique est actif (specs § 15.1) ; sinon l'écran est introuvable, comme toute section absente.
 */
export function DashboardSection({ shopId }: { shopId: string }) {
  const { loaded, retry } = useDashboardModule(shopId);
  if (loaded.status !== "ready") {
    return (
      <FiguresPending
        status={loaded.status}
        onRetry={retry}
        label="Ouverture du tableau de bord…"
        offlineMessage={DASHBOARD_OFFLINE}
      />
    );
  }
  if (!loaded.value) return <NotFoundPage />;
  return (
    <Suspense fallback={<Skeleton lines={4} label="Ouverture du tableau de bord…" />}>
      <DashboardRoute shopId={shopId} />
    </Suspense>
  );
}
