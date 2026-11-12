import type { ReactNode } from "react";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { Button, EmptyState, Skeleton } from "../../shared/ui";
import type { Loaded } from "../expenses/useLoad";

export interface ScreenFrameProps<T> {
  title: string;
  onBack: () => void;
  /** Lecture de l'écran : squelette, « Connexion nécessaire » ou contenu. */
  loaded: Loaded<T>;
  onRetry: () => void;
  children: (value: T) => ReactNode;
}

/** Cadre d'un écran des Réglages : retour au sommaire, titre, état de la lecture. */
export function ScreenFrame<T>({ title, onBack, loaded, onRetry, children }: ScreenFrameProps<T>) {
  return (
    <div className="flex flex-col gap-5">
      <Button variant="ghost" icon={ArrowLeft} onClick={onBack}>
        Retour aux réglages
      </Button>
      <h1 className="m-0 text-title font-bold text-text">{title}</h1>
      {loaded.status === "loading" && <Skeleton lines={4} label={`Chargement : ${title}…`} />}
      {loaded.status === "offline" && (
        <EmptyState
          message="Connexion nécessaire pour ouvrir les réglages."
          action={
            <Button variant="secondary" icon={RefreshCw} onClick={onRetry}>
              Réessayer
            </Button>
          }
        />
      )}
      {loaded.status === "ready" && children(loaded.value)}
    </div>
  );
}
