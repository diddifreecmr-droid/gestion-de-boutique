import type { ExpensePage } from "../../core/gateways/expensesContract";
import { formatMoney } from "../../shared/format";
import { barWidth } from "./barWidth";
import { categoryName, type References } from "./references";

/**
 * Répartition par catégorie (UC-DEP-03) en barres simples : composition de tokens, sans
 * bibliothèque de graphiques. Le montant et la part sont écrits : la barre ne porte rien seule.
 */
export function CategoryBars({
  refs,
  totals,
}: {
  refs: References;
  totals: ExpensePage["totals"];
}) {
  if (totals.amount === 0) return null;
  const rows = [...totals.by_category].sort((a, b) => b.amount - a.amount);
  return (
    <section aria-labelledby="expense-by-category" className="flex flex-col gap-2">
      <h2 id="expense-by-category" className="m-0 text-title-sm font-semibold text-text">
        Par catégorie
      </h2>
      <ul className="m-0 flex list-none flex-col gap-4 rounded-lg bg-surface p-4 shadow-card">
        {rows.map((row) => {
          const share = Math.round((row.amount / totals.amount) * 100);
          return (
            <li key={row.category_id} className="flex flex-col gap-1">
              <span className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-body text-text">{categoryName(refs, row.category_id)}</span>
                <span className="text-body tabular-nums text-text">
                  {`${formatMoney(row.amount)} · ${String(share)} %`}
                </span>
              </span>
              <span aria-hidden="true" className="block h-3 w-full rounded-sm bg-primary-soft">
                <span
                  className={`block h-3 rounded-sm bg-primary ${barWidth(row.amount, totals.amount)}`}
                />
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
