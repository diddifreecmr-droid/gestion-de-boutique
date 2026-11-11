import { Check } from "lucide-react";
import { ConfirmDialog } from "../../shared/ui";
import type { PurchaseDraft } from "./draft";
import { priceGapText, type PriceGap } from "./priceGap";

export interface PriceGapDialogProps {
  /** Lignes signalées par le serveur ; `null` : pas de confirmation en cours. */
  gaps: readonly PriceGap[] | null;
  draft: PurchaseDraft;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Nom de l'article de la ligne signalée (rang 0-based de la saisie envoyée). */
function articleOf(draft: PurchaseDraft, gap: PriceGap): string {
  const line = draft.lines[gap.line];
  if (line?.article === null || line === undefined) {
    throw new Error(`Écart de prix sur une ligne inconnue : ${String(gap.line)}`);
  }
  return line.article.name;
}

/**
 * Confirmation d'un prix très différent du dernier coût (UC-ACH-01, écart de plus de 30 %) :
 * « Le dernier achat était à 520 000 FCFA. Confirmer 52 000 FCFA ? », pour éviter un zéro
 * oublié. « Retour » laisse corriger le prix ; confirmer renvoie la même saisie.
 */
export function PriceGapDialog({ gaps, draft, onConfirm, onCancel }: PriceGapDialogProps) {
  if (gaps === null) return null;
  return (
    <ConfirmDialog
      open
      title="Prix très différent du dernier achat"
      confirmLabel="Confirmer le prix"
      confirmIcon={Check}
      cancelLabel="Corriger le prix"
      onConfirm={onConfirm}
      onCancel={onCancel}
    >
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {gaps.map((gap) => (
          <li key={gap.line}>
            {gaps.length > 1 || draft.lines.length > 1 ? (
              <>
                <strong>{articleOf(draft, gap)}</strong> : {priceGapText(gap)}
              </>
            ) : (
              priceGapText(gap)
            )}
          </li>
        ))}
      </ul>
    </ConfirmDialog>
  );
}
