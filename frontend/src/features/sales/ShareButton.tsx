import { Share2 } from "lucide-react";
import { Button } from "../../shared/ui";

/** Raison affichée sous « Partager » : le PDF chargé à la demande arrive ensuite (D9). */
export const SHARE_PENDING = "Partage PDF : à venir";

/** « Partager » (UC-VEN-04) : désactivé, avec sa raison, tant que le PDF n'est pas livré. */
export function ShareButton() {
  return (
    <Button variant="secondary" icon={Share2} fullWidth disabledReason={SHARE_PENDING}>
      Partager
    </Button>
  );
}
