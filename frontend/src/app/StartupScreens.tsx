import { RefreshCw } from "lucide-react";
import { useSession } from "../core/services/servicesContext";
import { Button, EmptyState, Skeleton } from "../shared/ui";
import { AppBanners } from "./AppBanners";

/** Restauration silencieuse de la session en cours. */
export function RestoringScreen() {
  return (
    <main className="mx-auto flex w-full max-w-150 flex-col gap-4 p-4">
      <Skeleton lines={3} label="Ouverture de votre session…" />
    </main>
  );
}

/** Restauration impossible (réseau, serveur) : le motif est affiché, on peut réessayer. */
export function RestoreFailedScreen({ error }: { error: Error }) {
  const session = useSession();
  return (
    <>
      <AppBanners />
      <main className="mx-auto flex w-full max-w-150 flex-col gap-4 p-4">
        <h1 className="m-0 text-title font-bold text-text">Session non ouverte</h1>
        <EmptyState
          message={`Impossible d'ouvrir votre session : ${error.message}`}
          action={
            <Button icon={RefreshCw} onClick={() => void session.retryRestore()}>
              Réessayer
            </Button>
          }
        />
      </main>
    </>
  );
}
