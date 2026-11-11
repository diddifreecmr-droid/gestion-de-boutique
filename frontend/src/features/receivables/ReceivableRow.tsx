import { Link } from "react-router";
import type { Receivable } from "../../core/gateways/receivablesContract";
import { formatDate, formatMoney } from "../../shared/format";
import { daysText } from "./labels";
import { originText } from "./receivableRules";
import { VIEW } from "./receivablesNav";
import { StatusBadge } from "./StatusBadge";

/** Classes d'une ligne ouvrable (tokens seulement, comme `ListCardRow`). */
const ROW_LINK =
  "flex min-h-16 items-center gap-4 px-4 py-3 text-left no-underline hover:bg-primary-soft " +
  "transition-colors duration-(--duration-fast) ease-out outline-hidden " +
  "focus-visible:outline-2 focus-visible:outline-solid focus-visible:-outline-offset-2 " +
  "focus-visible:outline-primary";

/**
 * Ligne de la liste (UC-CRE-04) : client, initial, versé, reste (violet = argent dû),
 * ouverture, dernier versement, ancienneté, statut. Un lien : la fiche a sa propre adresse.
 */
export function ReceivableRow({ receivable }: { receivable: Receivable }) {
  const last =
    receivable.last_installment_on === null
      ? "aucun versement"
      : `dernier versement le ${formatDate(receivable.last_installment_on)}`;
  const due = receivable.status === "open" ? "text-credit-text" : "text-text-muted";
  return (
    <li>
      <Link to={`?vue=${VIEW.detail}&id=${encodeURIComponent(receivable.id)}`} className={ROW_LINK}>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="text-lead break-words text-text">{receivable.customer.name}</span>
          <span className="text-body break-words text-text-muted">{originText(receivable)}</span>
          <span className="text-body text-text-muted">
            Initial {formatMoney(receivable.initial_amount)} · versé{" "}
            {formatMoney(receivable.total_paid)}
          </span>
          <span className="text-body text-text-muted">
            Ouverte le {formatDate(receivable.opened_on)} ({daysText(receivable.seniority_days)}) ·{" "}
            {last}
          </span>
        </span>
        <span className="flex shrink-0 flex-col items-end gap-1">
          <span className="text-body text-text-muted">Reste</span>
          <span className={`text-lead font-semibold tabular-nums ${due}`}>
            {formatMoney(receivable.remaining)}
          </span>
          <StatusBadge status={receivable.status} />
        </span>
      </Link>
    </li>
  );
}
