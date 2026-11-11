import { Link } from "react-router";
import type { SaleResult } from "../../core/gateways/salesContract";
import { formatDate, formatMoney, formatQuantity, formatTime } from "../../shared/format";
import { Badge } from "../../shared/ui";
import { modeName, sellerName, type SaleRefs } from "./saleRefs";
import { saleLink } from "./salesNav";

/** Classes d'une ligne ouvrable (tokens seulement, comme `ListCardRow`). */
const ROW_LINK =
  "flex min-h-16 items-center gap-4 px-4 py-3 text-left no-underline hover:bg-primary-soft " +
  "transition-colors duration-(--duration-fast) ease-out outline-hidden " +
  "focus-visible:outline-2 focus-visible:outline-solid focus-visible:-outline-offset-2 " +
  "focus-visible:outline-primary";

/** « 3 × Haojue HJ125-8, Sanya SY125-8 ». */
function articlesText(sale: SaleResult): string {
  return sale.lines
    .map((line) =>
      Number(line.quantity) === 1
        ? line.article_name
        : `${formatQuantity(line.quantity)} × ${line.article_name}`,
    )
    .join(", ");
}

/**
 * Ligne de la liste (UC-VEN-05) : numéro, heure, articles, total, mode, vendeur (propriétaire),
 * pastilles « Crédit » / « Annulée ». Annulée (RG-T03) : la ligne reste, barrée, sauf la pastille.
 */
export function SaleRow({
  refs,
  sale,
  today,
}: {
  refs: SaleRefs;
  sale: SaleResult;
  today: string;
}) {
  const struck = sale.status === "cancelled" ? "text-text-muted line-through" : "";
  const modes = [...new Set(sale.payments.map((p) => modeName(refs, p.mode_id)))];
  const when = sale.sold_on === today ? formatTime(sale.sold_at) : formatDate(sale.sold_on);
  const details = [
    when,
    articlesText(sale),
    ...(modes.length === 0 ? [] : [modes.join(" + ")]),
    ...(refs.role === "owner" ? [`par ${sellerName(refs, sale.seller_id)}`] : []),
  ].join(" · ");
  return (
    <li>
      <Link to={saleLink(sale.id)} className={ROW_LINK}>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className={`font-mono text-lead text-text ${struck}`}>{sale.number}</span>
          <span className={`break-words text-body text-text-muted ${struck}`}>{details}</span>
        </span>
        <span className="flex shrink-0 flex-col items-end gap-1">
          <span className={`text-lead font-semibold tabular-nums text-text ${struck}`}>
            {formatMoney(sale.total)}
          </span>
          {sale.status === "cancelled" && <Badge status="danger">Annulée</Badge>}
          {sale.status !== "cancelled" && sale.kind === "credit" && (
            <Badge status="credit">Crédit</Badge>
          )}
        </span>
      </Link>
    </li>
  );
}
