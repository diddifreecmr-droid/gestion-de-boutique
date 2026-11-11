import { useId, useState } from "react";
import { Printer, XCircle } from "lucide-react";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import type { Installment, Receivable } from "../../core/gateways/receivablesContract";
import { formatDate, formatMoney, formatTime } from "../../shared/format";
import { Badge, Button, ConfirmDialog } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { memberName, modeName, type References } from "./references";
import { useAction } from "./useAction";

export interface InstallmentsSectionProps {
  shopId: string;
  refs: References;
  receivable: Receivable;
  onChanged: (receivable: Receivable) => void;
  onPrint: (installmentId: string) => void;
}

/** RG-T03 : « Annulé le 11/11/2026 à 14 h 32 par Awa Bello — motif : erreur de saisie ». */
function cancelText(refs: References, item: Installment): string {
  if (item.cancelled_at === null) throw new Error(`Versement ${item.number} annulé sans date`);
  const when = `${formatDate(item.cancelled_at)} à ${formatTime(item.cancelled_at)}`;
  return `Annulé le ${when} par ${memberName(refs, item.cancelled_by)} — motif : ${item.cancel_reason ?? ""}`;
}

function Row(props: {
  refs: References;
  item: Installment;
  manageable: boolean;
  onCancel: () => void;
  onPrint: () => void;
}) {
  const { refs, item } = props;
  const cancelled = item.status === "cancelled";
  const struck = cancelled ? "text-text-muted line-through" : "";
  const reference = item.reference === null ? "" : ` (${item.reference})`;
  return (
    <li className="flex flex-col gap-2 px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 flex-col">
          <span className={`text-lead text-text ${struck}`}>
            {item.number} — {formatDate(item.paid_on)}
          </span>
          <span className={`text-body break-words text-text-muted ${struck}`}>
            {modeName(refs, item.mode_id)}
            {reference}
            {item.nature === "recovery" ? " · récupération sur perte" : ""}
          </span>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className={`text-lead font-semibold tabular-nums text-text ${struck}`}>
            {formatMoney(item.amount)}
          </span>
          {cancelled && <Badge status="danger">Annulé</Badge>}
        </div>
      </div>
      {cancelled && <p className="m-0 text-body text-text">{cancelText(refs, item)}</p>}
      {!cancelled && (
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" icon={Printer} onClick={props.onPrint}>
            Reçu {item.number}
          </Button>
          {props.manageable && (
            <Button variant="ghost" icon={XCircle} onClick={props.onCancel}>
              Annuler {item.number}
            </Button>
          )}
        </div>
      )}
    </li>
  );
}

/** Versements de la créance ; le propriétaire annule un versement avec un motif (UC-CRE-08). */
export function InstallmentsSection(props: InstallmentsSectionProps) {
  const { shopId, refs, receivable, onChanged } = props;
  const { gateway } = useReceivablesDeps();
  const titleId = useId();
  const [target, setTarget] = useState<Installment | null>(null);
  const action = useAction();
  const items = receivable.installments;
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-2">
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Versements
      </h2>
      {items.length === 0 ? (
        <p className="m-0 text-body text-text-muted">Aucun versement pour l'instant.</p>
      ) : (
        <ul className="m-0 list-none divide-y divide-border rounded-lg bg-surface p-0 shadow-card">
          {items.map((item) => (
            <Row
              key={item.id}
              refs={refs}
              item={item}
              manageable={receivable.manageable}
              onCancel={() => {
                setTarget(item);
              }}
              onPrint={() => {
                props.onPrint(item.id);
              }}
            />
          ))}
        </ul>
      )}
      {action.message !== null && <FormMessage text={action.message} />}
      <ConfirmDialog
        open={target !== null}
        title={`Annuler le versement ${target?.number ?? ""} ?`}
        confirmLabel="Annuler le versement"
        confirmIcon={XCircle}
        requireReason
        onCancel={() => {
          setTarget(null);
        }}
        onConfirm={(reason) => {
          if (target === null || reason === null) throw new Error("Annulation sans versement");
          const id = target.id;
          setTarget(null);
          void action.run(async () => {
            onChanged((await gateway.cancelInstallment(shopId, id, reason)).receivable);
          });
        }}
      >
        Le reste à payer sera recalculé ; une créance soldée redevient « En cours ».
      </ConfirmDialog>
    </section>
  );
}
