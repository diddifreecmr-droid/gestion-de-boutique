import { RotateCw, WifiOff } from "lucide-react";
import { Button, EmptyState, Skeleton } from "../../shared/ui";

/** Message affiché à la place des montants hors connexion (UC-TDB-01, RG-T25). */
export const FIGURES_OFFLINE = "Chiffres disponibles avec internet";

/** Chiffres en cours de lecture, ou absents faute de réseau : jamais de chiffre en cache. */
export function FiguresPending({
  status,
  onRetry,
  label = "Lecture des chiffres…",
}: {
  status: "loading" | "offline";
  onRetry: () => void;
  label?: string;
}) {
  if (status === "loading") return <Skeleton lines={4} label={label} />;
  return (
    <EmptyState
      icon={WifiOff}
      message={FIGURES_OFFLINE}
      action={
        <Button variant="secondary" icon={RotateCw} onClick={onRetry}>
          Réessayer
        </Button>
      }
    />
  );
}
