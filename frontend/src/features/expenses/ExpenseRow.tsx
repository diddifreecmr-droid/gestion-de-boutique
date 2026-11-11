import { Link } from "react-router";
import type { Expense } from "../../core/gateways/expensesContract";
import { formatDate, formatMoney } from "../../shared/format";
import { Badge } from "../../shared/ui";
import { VIEW } from "./expenseNav";
import { cancellationText } from "./expenseText";
import { authorName, categoryName, type References } from "./references";

/** Classes d'une ligne ouvrable (tokens seulement, comme `ListCardRow`). */
const ROW_LINK =
  "flex min-h-16 items-center gap-4 px-4 py-3 text-left no-underline hover:bg-primary-soft " +
  "transition-colors duration-(--duration-fast) ease-out outline-hidden " +
  "focus-visible:outline-2 focus-visible:outline-solid focus-visible:-outline-offset-2 " +
  "focus-visible:outline-primary";

/**
 * Ligne de la liste. Annulée (RG-T03) : la ligne reste, texte barré en text-muted, sauf la
 * pastille « Annulée » et la mention « Annulée le … par … — motif : … » (design-system § 6.4).
 * Un lien (et non un bouton) : la fiche a sa propre adresse.
 */
export function ExpenseRow({ refs, expense }: { refs: References; expense: Expense }) {
  const cancelled = expense.status === "cancelled";
  const struck = cancelled ? "text-text-muted line-through" : "";
  const tags = expense.tags.map((tag) => tag.name).join(", ");
  const details = [formatDate(expense.spent_on), authorName(refs, expense.created_by), tags]
    .filter((part) => part !== "")
    .join(" · ");
  const mention = cancellationText(refs, expense);
  return (
    <li>
      <Link to={`?vue=${VIEW.detail}&id=${encodeURIComponent(expense.id)}`} className={ROW_LINK}>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className={`text-lead text-text ${struck}`}>
            {categoryName(refs, expense.category_id)}{" "}
            <span className="font-mono text-body text-text-muted">{expense.number}</span>
          </span>
          <span className={`text-body text-text-muted ${struck}`}>{details}</span>
          {mention !== null && <span className="text-body text-text">{mention}</span>}
        </span>
        <span className="flex shrink-0 flex-col items-end gap-1">
          <span className={`text-lead font-semibold tabular-nums text-text ${struck}`}>
            {formatMoney(expense.amount)}
          </span>
          {cancelled && <Badge status="danger">Annulée</Badge>}
        </span>
      </Link>
    </li>
  );
}
