import { RotateCw, WifiOff } from "lucide-react";
import { Button, EmptyState, Skeleton } from "../../shared/ui";

/** Message affiché à la place des montants hors connexion (UC-TDB-01, RG-T25). */
export const FIGURES_OFFLINE = "Chiffres disponibles avec internet";

/** Chiffres en cours de lecture, ou absents faute de réseau : jamais de chiffre en cache. */
export function FiguresPending({
  status,
  onRetry,
  label = "Lecture des chiffres…",
  offlineMessage = FIGURES_OFFLINE,
}: {
  status: "loading" | "offline";
  onRetry: () => void;
  label?: string;
  offlineMessage?: string;
}) {
  if (status === "loading") return <Skeleton lines={4} label={label} />;
  return (
    <EmptyState
      icon={WifiOff}
      message={offlineMessage}
      action={
        <Button variant="secondary" icon={RotateCw} onClick={onRetry}>
          Réessayer
        </Button>
      }
    />
  );
}
