import type { ProfileFieldResponse } from "../../core/gateways/catalogAdminContract";
import { costsOf, pricesOf, type ArticleView } from "./articleView";
import { FactsCard, type Fact } from "./FactsCard";
import { moneyOr, NOT_COMPUTABLE, NOT_SET } from "./money";

const EMPTY = "—";

function shown(value: unknown): string {
  if (value === null || value === undefined || value === "") return EMPTY;
  if (typeof value === "boolean") return value ? "Oui" : "Non";
  if (typeof value === "string" || typeof value === "number") return String(value);
  throw new Error(`Valeur de champ inattendue : ${JSON.stringify(value)}`);
}

/** Détails, prix et coûts de la fiche — seulement ce que la vue du rôle contient (TR-05). */
export function ArticleFacts({
  view,
  fields,
}: {
  view: ArticleView;
  fields: readonly ProfileFieldResponse[];
}) {
  const details: Fact[] = [
    ...fields.map((spec) => ({ label: spec.label, value: shown(view.values[spec.code]) })),
    {
      label: "Seuil d'alerte",
      value:
        view.alertThreshold === null
          ? `${view.effectiveThreshold} (réglage de la boutique)`
          : view.alertThreshold,
    },
    { label: "Notes", value: shown(view.notes) },
  ];
  const prices = pricesOf(view);
  const costs = costsOf(view);
  return (
    <>
      <FactsCard title="Détails" facts={details} />
      {prices !== null && (
        <FactsCard
          title="Prix de vente"
          facts={[
            { label: "Prix de base", value: moneyOr(prices.basePrice, NOT_SET) },
            ...(prices.minPriceActive || prices.minPrice !== null
              ? [{ label: "Prix minimum", value: moneyOr(prices.minPrice, NOT_SET) }]
              : []),
          ]}
        />
      )}
      {costs !== null && (
        <FactsCard
          title="Coûts"
          facts={[
            { label: "Dernier coût d'achat", value: moneyOr(costs.lastCost, NOT_COMPUTABLE) },
            { label: "Coût moyen (CMP)", value: moneyOr(costs.wac, NOT_COMPUTABLE) },
          ]}
        />
      )}
    </>
  );
}
