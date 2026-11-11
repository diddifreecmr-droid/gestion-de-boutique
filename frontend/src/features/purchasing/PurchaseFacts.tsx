import { formatDate, formatMoney, formatTime } from "../../shared/format";
import { perStockUnit } from "./draftCosting";
import { feeText } from "./fees";
import { locationName, supplierName, type References } from "./references";
import { quantityWithUnit } from "./units";
import { articleName, type LoadedPurchase } from "./usePurchase";

type Fact = [label: string, value: string];

function Facts({ label, facts, struck }: { label: string; facts: Fact[]; struck: string }) {
  return (
    <section
      aria-label={label}
      className="flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card"
    >
      <h2 className="m-0 text-title-sm font-semibold text-text">{label}</h2>
      <dl className="m-0 flex flex-col gap-2">
        {facts.map(([name, value], index) => (
          <div
            key={`${name}-${String(index)}`}
            className="flex flex-wrap items-baseline justify-between gap-2"
          >
            <dt className="min-w-0 break-words text-body text-text-muted">{name}</dt>
            <dd className={`m-0 min-w-0 break-words text-right text-lead tabular-nums ${struck}`}>
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/** « 20 × 520 000 FCFA », puis « soit 9,1 m » quand l'unité saisie n'est pas celle du stock. */
function lineFacts(loaded: LoadedPurchase): Fact[] {
  return loaded.purchase.lines.flatMap((line) => {
    const name = articleName(loaded.articles, line.article_id);
    const entered = `${quantityWithUnit(line.quantity, line.unit)} × ${formatMoney(line.unit_price)}`;
    const facts: Fact[] = [[name, entered]];
    if (line.unit !== line.stock_unit) {
      facts.push([
        "Quantité en stock",
        `soit ${quantityWithUnit(line.stock_quantity, line.stock_unit)}`,
      ]);
    }
    facts.push(["Total de la ligne", formatMoney(line.total)]);
    if (line.fee_share > 0) facts.push(["Part des frais", formatMoney(line.fee_share)]);
    facts.push([
      "Coût unitaire final",
      `${formatMoney(line.final_unit_cost)} ${perStockUnit(line.stock_unit)}`,
    ]);
    return facts;
  });
}

/** Contenu d'un achat (UC-ACH-05) : en-tête, lignes avec coût unitaire final, frais. */
export function PurchaseFacts({ refs, loaded }: { refs: References; loaded: LoadedPurchase }) {
  const { purchase } = loaded;
  const struck = purchase.status === "cancelled" ? "text-text-muted line-through" : "text-text";
  const header: Fact[] = [
    ["Fournisseur", supplierName(refs, purchase.supplier_id)],
    ["Date de l'achat", formatDate(purchase.purchase_date)],
    ["Lieu de réception", locationName(refs, purchase.location_id)],
  ];
  if (purchase.invoice_ref !== null) header.push(["Facture n°", purchase.invoice_ref]);
  if (purchase.note !== null) header.push(["Note", purchase.note]);
  header.push([
    "Saisi le",
    `${formatDate(purchase.received_at)} à ${formatTime(purchase.received_at)}`,
  ]);
  return (
    <>
      <Facts label="Achat" facts={header} struck={struck} />
      <Facts label="Articles" facts={lineFacts(loaded)} struck={struck} />
      {purchase.fees.length > 0 && (
        <Facts
          label="Frais"
          struck={struck}
          facts={purchase.fees.map((fee): Fact => [
            feeText(fee.kind, fee.label),
            formatMoney(fee.amount),
          ])}
        />
      )}
    </>
  );
}
