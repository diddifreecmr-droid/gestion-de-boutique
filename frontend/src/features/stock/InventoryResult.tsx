import type { Inventory, InventoryLine } from "../../core/gateways/stockContract";
import { formatDate, formatTime } from "../../shared/format";
import { Badge } from "../../shared/ui";
import { moneyOr, NOT_COMPUTABLE } from "../catalog/money";
import { Facts, type Fact } from "./Facts";
import { WarningText } from "./Notice";
import { isZero, quantityText, signedQuantityText } from "./quantities";

function settled(line: InventoryLine, field: "theoretical" | "difference" | "counted"): string {
  const value = line[field];
  if (value === null || value === undefined) {
    throw new Error(`Inventaire validé sans « ${field} » pour « ${line.display_name} »`);
  }
  return value;
}

/** Une ligne en écart : théorique, compté, écart, valeur au CMP, motif (UC-STK-07, étape 3). */
function GapCard({ line }: { line: InventoryLine }) {
  const unit = line.stock_unit;
  const facts: Fact[] = [
    {
      label: "Quantité prévue (théorique)",
      value: quantityText(settled(line, "theoretical"), unit),
    },
    { label: "Quantité comptée", value: quantityText(settled(line, "counted"), unit) },
    { label: "Écart", value: signedQuantityText(settled(line, "difference"), unit), strong: true },
  ];
  // `gap_value` n'est posé que pour qui voit les coûts ; `null` = CMP inconnu.
  if (line.gap_value !== undefined) {
    facts.push({
      label: "Valeur de l'écart (CMP)",
      value: moneyOr(line.gap_value, NOT_COMPUTABLE),
    });
  }
  facts.push({ label: "Motif", value: line.reason ?? "—" });
  return (
    <li className="flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card">
      <h3 className="m-0 break-words text-lead font-semibold text-text">{line.display_name}</h3>
      <Facts facts={facts} />
    </li>
  );
}

/** Inventaire validé : écarts figés, chacun devenu un ajustement « écart d'inventaire ». */
export function InventoryResult({ inventory }: { inventory: Inventory }) {
  const gaps = inventory.lines.filter((line) => !isZero(settled(line, "difference")));
  const closed = inventory.closed_at;
  const summary: Fact[] = [{ label: "Écarts", value: String(inventory.gap_count ?? gaps.length) }];
  if (inventory.gap_value !== undefined) {
    summary.push({
      label: "Valeur des écarts (CMP)",
      value: moneyOr(inventory.gap_value, NOT_COMPUTABLE),
      strong: true,
    });
  }
  if (inventory.global_reason !== null)
    summary.push({ label: "Motif global", value: inventory.global_reason });
  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <Badge status="success">Validé</Badge>
        {closed !== null && (
          <span className="text-body text-text-muted">
            {`le ${formatDate(closed)} à ${formatTime(closed)}`}
          </span>
        )}
      </div>
      {inventory.sales_message !== null && <WarningText text={inventory.sales_message} />}
      <div className="rounded-lg bg-surface p-4 shadow-card">
        <Facts facts={summary} />
      </div>
      <h2 className="m-0 text-title-sm font-semibold text-text">Écarts</h2>
      {gaps.length === 0 ? (
        <p className="m-0 text-body text-text">Aucun écart : le stock compté est celui prévu.</p>
      ) : (
        <ul aria-label="Écarts d'inventaire" className="m-0 flex list-none flex-col gap-4 p-0">
          {gaps.map((line) => (
            <GapCard key={line.article_id} line={line} />
          ))}
        </ul>
      )}
      {inventory.lines.length > gaps.length && gaps.length > 0 && (
        <p className="m-0 text-body text-text-muted">
          {`${String(inventory.lines.length - gaps.length)} article(s) sans écart.`}
        </p>
      )}
    </>
  );
}
