import { lazy, Suspense } from "react";
import { Skeleton, TopBar, useToast } from "../shared/ui";
import { useSignedIn } from "../core/services/servicesContext";
import { NotFoundPage } from "./NotFoundPage";
import { AppBanners } from "./AppBanners";

/** Écrans de la console, chargés à la demande (seul l'administrateur les ouvre). */
const PlatformConsole = lazy(() => import("../features/platform/PlatformConsole"));

/**
 * Console de l'administrateur plateforme (TR-23) : boutiques, ouverture d'une boutique et de
 * son propriétaire, statut, droits d'offre, délégation ; « Mon compte » sous la liste des
 * boutiques seulement (accueil de la console), jamais répété sous la fiche d'une boutique.
 */
export function PlatformHome() {
  const me = useSignedIn();
  const toast = useToast();
  if (!me.isPlatformAdmin) return <NotFoundPage />;
  return (
    <div className="min-h-screen">
      <TopBar
        title="Console plateforme"
        alertCount={0}
        onAlertsClick={() => {
          toast.show({
            tone: "success",
            message: "Les alertes de la plateforme arrivent bientôt.",
          });
        }}
      />
      <AppBanners />
      <main className="mx-auto flex w-full max-w-150 flex-col gap-4 p-4">
        <Suspense fallback={<Skeleton lines={4} label="Ouverture de la console…" />}>
          <PlatformConsole />
        </Suspense>
      </main>
    </div>
  );
}
