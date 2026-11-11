import { Check, Send } from "lucide-react";
import { formatMoney } from "../../shared/format";
import { ActionBar, Badge, Button } from "../../shared/ui";

export type ApprovalState = "none" | "sending" | "pending";

export interface SaleActionBarProps {
  total: number;
  /** Le vendeur a un prix sous le minimum : il faut l'accord du propriétaire (UC-VEN-03). */
  needsApproval: boolean;
  approval: ApprovalState;
  submitting: boolean;
  onSubmit: () => void;
  onRequestApproval: () => void;
}

/**
 * Total et action principale, en bas de l'écran (§ 6.1, § 7.1). La barre reste au-dessus
 * de la barre de navigation (`sticky`), dans le flux de la page.
 */
export function SaleActionBar({
  total,
  needsApproval,
  approval,
  submitting,
  onSubmit,
  onRequestApproval,
}: SaleActionBarProps) {
  const summary = (
    <p className="m-0 flex items-baseline justify-between gap-4">
      <span>Total</span>
      <strong className="text-amount tabular-nums">{formatMoney(total)}</strong>
    </p>
  );
  return (
    <div className="sticky bottom-16 z-20 -mx-4">
      <ActionBar fixed={false} summary={summary}>
        {!needsApproval && (
          <Button size="lg" fullWidth icon={Check} loading={submitting} onClick={onSubmit}>
            Valider la vente
          </Button>
        )}
        {needsApproval && approval !== "pending" && (
          <Button
            variant="secondary"
            size="lg"
            fullWidth
            icon={Send}
            loading={approval === "sending"}
            onClick={onRequestApproval}
          >
            Demander l'accord du propriétaire
          </Button>
        )}
        {needsApproval && approval === "pending" && (
          <>
            <p className="m-0 flex flex-wrap items-center gap-2 text-body text-text">
              <Badge status="warning">En attente</Badge>
              <span>Demande envoyée au propriétaire. Elle expire au bout de 30 minutes.</span>
            </p>
            <Button
              size="lg"
              fullWidth
              icon={Check}
              disabledReason="En attente de l'accord du propriétaire, ou changez le prix"
            >
              Valider la vente
            </Button>
          </>
        )}
      </ActionBar>
    </div>
  );
}
