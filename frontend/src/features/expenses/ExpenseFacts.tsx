import type { Expense } from "../../core/gateways/expensesContract";
import { formatDate, formatMoney, formatTime } from "../../shared/format";
import { authorName, categoryName, locationName, modeName, type References } from "./references";

/** Contenu d'une dépense, en lignes « libellé : valeur » (texte barré si annulée, RG-T03). */
export function ExpenseFacts({ refs, expense }: { refs: References; expense: Expense }) {
  const struck = expense.status === "cancelled" ? "text-text-muted line-through" : "text-text";
  const lines: [string, string][] = [
    ["Montant", formatMoney(expense.amount)],
    ["Catégorie", categoryName(refs, expense.category_id)],
    ["Date", formatDate(expense.spent_on)],
    ["Mode de paiement", modeName(refs, expense.payment_mode_id)],
  ];
  if (expense.tags.length > 0) lines.push(["Tags", expense.tags.map((t) => t.name).join(", ")]);
  if (expense.description !== null) lines.push(["Description", expense.description]);
  if (expense.location_id !== null) {
    lines.push(["Lieu", locationName(refs, expense.location_id)]);
  }
  if (expense.beneficiary !== null) lines.push(["Bénéficiaire", expense.beneficiary]);
  const saved = `${formatDate(expense.received_at)} à ${formatTime(expense.received_at)}`;
  lines.push(["Saisie", `le ${saved} par ${authorName(refs, expense.created_by)}`]);
  return (
    <dl className="m-0 flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card">
      {lines.map(([label, value]) => (
        <div key={label} className="flex flex-wrap items-baseline justify-between gap-2">
          <dt className="text-body text-text-muted">{label}</dt>
          <dd className={`m-0 text-right text-lead tabular-nums ${struck}`}>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
