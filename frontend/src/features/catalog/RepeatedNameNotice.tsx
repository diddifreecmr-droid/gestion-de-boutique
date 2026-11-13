import { AlertTriangle, Check } from "lucide-react";
import { Button } from "../../shared/ui";

export interface RepeatedNameNoticeProps {
  name: string;
  /** Nom sans le mot répété (« Robe Bleu Marine »). */
  fixed: string;
  /** Remplace le nom saisi par `fixed` ; absent si le nom ne vient pas d'un seul champ. */
  onUse?: () => void;
}

/** Avertissement « mot répété » avant la création (garde-fou du nom, VOC-04). */
export function RepeatedNameNotice({ name, fixed, onUse }: RepeatedNameNoticeProps) {
  return (
    <div role="status" className="flex flex-col gap-2">
      <p className="m-0 flex items-start gap-2 text-body text-warning-text">
        <AlertTriangle aria-hidden="true" className="size-6 shrink-0" />
        <span>
          Mot répété dans le nom « {name} ». Nom proposé : « {fixed} ». Appuyez de nouveau sur «
          Créer l'article » pour garder le nom tel quel.
        </span>
      </p>
      {onUse !== undefined && (
        <Button variant="secondary" fullWidth icon={Check} onClick={onUse}>
          Utiliser « {fixed} »
        </Button>
      )}
    </div>
  );
}
