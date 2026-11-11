import { WifiOff } from "lucide-react";
import { EmptyState, Skeleton } from "../../shared/ui";

/** Écran en attente de sa lecture, ou « Connexion nécessaire » si le réseau manque. */
export function LoadingOrOffline({
  title,
  status,
}: {
  title: string;
  status: "loading" | "offline";
}) {
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">{title}</h1>
      {status === "loading" ? (
        <Skeleton lines={4} />
      ) : (
        <EmptyState icon={WifiOff} message="Connexion nécessaire pour afficher cet écran." />
      )}
    </>
  );
}
