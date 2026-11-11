import { formatMoney } from "../../shared/format";
import type { PurchaseDraft } from "./draft";
import { draftCosting, perStockUnit } from "./draftCosting";

function Row({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <dt className="min-w-0 break-words text-body text-text-muted">{label}</dt>
      <dd
        className={`m-0 text-right tabular-nums text-text ${strong ? "text-amount font-bold" : "text-lead"}`}
      >
        {value}
      </dd>
    </div>
  );
}

/**
 * Récapitulatif (UC-ACH-01 étape 5) : total marchandise, total des frais, coût unitaire final
 * de chaque ligne (RG-T10). Calcul indicatif, même règle que le serveur, qui reste juge.
 */
export function CostSummary({ draft }: { draft: PurchaseDraft }) {
  const result = draftCosting(draft);
  if (result === null) return null;
  const { costing, ready } = result;
  return (
    <section
      aria-label="Récapitulatif"
      className="flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card"
    >
      <h2 className="m-0 text-title-sm font-semibold text-text">Récapitulatif</h2>
      <dl className="m-0 flex flex-col gap-2">
        <Row label="Total marchandise" value={formatMoney(costing.merchandise)} />
        <Row label="Total des frais" value={formatMoney(costing.fees)} />
        {ready.map((line, index) => {
          const cost = costing.lines[index]?.finalUnitCost ?? null;
          const value =
            cost === null
              ? "non calculable"
              : `${formatMoney(cost)} ${perStockUnit(line.stockUnit)}`;
          return (
            <Row
              key={`${line.name}-${String(index)}`}
              label={`Coût unitaire final — ${line.name}`}
              value={value}
            />
          );
        })}
        <Row label="Total de l'achat" value={formatMoney(costing.total)} strong />
      </dl>
      <p className="m-0 text-body text-text-muted">
        Coûts calculés à titre indicatif ; ils sont confirmés à l'enregistrement.
      </p>
    </section>
  );
}
