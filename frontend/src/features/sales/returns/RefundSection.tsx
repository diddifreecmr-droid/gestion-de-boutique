import { useId } from "react";
import type { SaleResult } from "../../../core/gateways/salesContract";
import { formatMoney } from "../../../shared/format";
import { AmountField, ChoiceChips, TextField } from "../../../shared/ui";
import type { ReturnChecks, ReturnDraft } from "./returnDraft";

export interface RefundSectionProps {
  sale: SaleResult;
  modes: readonly { id: string; name: string }[];
  draft: ReturnDraft;
  checks: ReturnChecks;
  showErrors: boolean;
  update: (patch: Partial<ReturnDraft>) => void;
}

/**
 * Retour simple (UC-VEN-09) : valeur rendue ; vente à crédit : baisse de la créance (calculée
 * par le serveur) ; remboursement facultatif plafonné (≤ payé, net des remboursements), avec
 * son mode et sa date.
 */
export function RefundSection({
  sale,
  modes,
  draft,
  checks,
  showErrors,
  update,
}: RefundSectionProps) {
  const titleId = useId();
  const { reduction, refundMax } = checks.settlement;
  const error = (text: string | undefined) => (showErrors ? text : undefined);
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-4 rounded-lg bg-surface p-4 shadow-card"
    >
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Remboursement
      </h2>
      <dl className="m-0 grid grid-cols-2 gap-x-4 text-body text-text">
        <dt className="text-text-muted">Valeur rendue</dt>
        <dd className="m-0 text-right tabular-nums">{formatMoney(checks.value)}</dd>
        {sale.kind === "credit" && (
          <>
            <dt className="text-text-muted">Baisse de la créance</dt>
            <dd className="m-0 text-right tabular-nums">{formatMoney(reduction)}</dd>
          </>
        )}
        <dt className="text-text-muted">Remboursable au plus</dt>
        <dd className="m-0 text-right font-semibold tabular-nums">{formatMoney(refundMax)}</dd>
      </dl>
      {refundMax === 0 ? (
        <p className="m-0 text-body text-text-muted">
          {sale.kind === "credit"
            ? "Rien à rembourser : la valeur rendue baisse la créance du client."
            : "Rien à rembourser pour ce retour."}
        </p>
      ) : (
        <>
          <AmountField
            label="Montant remboursé"
            hint="Laissez vide si rien n'est rendu au client"
            value={draft.refundAmount}
            error={error(checks.refund)}
            onChange={(refundAmount) => {
              update({ refundAmount });
            }}
          />
          {(draft.refundAmount ?? 0) > 0 && (
            <>
              <ChoiceChips
                label="Mode du remboursement"
                options={modes.map((mode) => ({ value: mode.id, label: mode.name }))}
                value={draft.modeId}
                onChange={(modeId) => {
                  update({ modeId });
                }}
              />
              {showErrors && checks.mode !== undefined && (
                <p className="m-0 text-body text-danger-text">{checks.mode}</p>
              )}
              <TextField
                label="Date du remboursement"
                type="date"
                value={draft.refundOn}
                error={error(checks.refundOn)}
                onChange={(event) => {
                  update({ refundOn: event.target.value });
                }}
              />
            </>
          )}
        </>
      )}
    </section>
  );
}
