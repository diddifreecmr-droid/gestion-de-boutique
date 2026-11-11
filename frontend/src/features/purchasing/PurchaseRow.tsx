import { Link } from "react-router";
import type { Purchase } from "../../core/gateways/purchasingContract";
import { formatDate, formatMoney } from "../../shared/format";
import { PaymentBadge } from "./PaymentBadge";
import { VIEW } from "./purchasingNav";
import { locationName, supplierName, type References } from "./references";

/** Classes d'une ligne ouvrable (tokens seulement, comme `ListCardRow`). */
const ROW_LINK =
  "flex min-h-16 items-center gap-4 px-4 py-3 text-left no-underline hover:bg-primary-soft " +
  "transition-colors duration-(--duration-fast) ease-out outline-hidden " +
  "focus-visible:outline-2 focus-visible:outline-solid focus-visible:-outline-offset-2 " +
  "focus-visible:outline-primary";

const articles = (count: number) => (count === 1 ? "1 article" : `${String(count)} articles`);

/**
 * Ligne de la liste (UC-ACH-05) : numéro, date, fournisseur, lieu, nombre d'articles, total,
 * statut de paiement. Annulé (RG-T03) : la ligne reste, barrée, sauf la pastille. Un lien :
 * la fiche a sa propre adresse.
 */
export function PurchaseRow({ refs, purchase }: { refs: References; purchase: Purchase }) {
  const struck = purchase.status === "cancelled" ? "text-text-muted line-through" : "";
  const details = [
    formatDate(purchase.purchase_date),
    locationName(refs, purchase.location_id),
    articles(purchase.article_count),
  ].join(" · ");
  return (
    <li>
      <Link to={`?vue=${VIEW.detail}&id=${encodeURIComponent(purchase.id)}`} className={ROW_LINK}>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className={`break-words text-lead text-text ${struck}`}>
            {supplierName(refs, purchase.supplier_id)}{" "}
            <span className="font-mono text-body text-text-muted">{purchase.number}</span>
          </span>
          <span className={`break-words text-body text-text-muted ${struck}`}>{details}</span>
        </span>
        <span className="flex shrink-0 flex-col items-end gap-1">
          <span className={`text-lead font-semibold tabular-nums text-text ${struck}`}>
            {formatMoney(purchase.total)}
          </span>
          <PaymentBadge purchase={purchase} />
        </span>
      </Link>
    </li>
  );
}
