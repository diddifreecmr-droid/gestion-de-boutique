import { History } from "lucide-react";
import { Button } from "../../shared/ui";
import { moneyOr, NOT_COMPUTABLE, NOT_SET } from "../catalog/money";
import { Facts, type Fact } from "./Facts";
import { StockBadge } from "./Notice";
import { isZero, quantityText } from "./quantities";
import { basePriceOf, costsOf, type StockLine } from "./stockView";

/** Quantités : un lieu par ligne (ordre des lieux), « En route », puis « Total ». */
function quantityFacts(line: StockLine): Fact[] {
  const qty = (value: string) => quantityText(value, line.unit);
  const places = line.places.map((place) => ({
    label: place.name,
    value: isZero(place.damaged)
      ? qty(place.sellable)
      : `${qty(place.sellable)} (+ ${qty(place.damaged)} abîmé)`,
  }));
  return [
    ...places,
    { label: "En route", value: qty(line.incoming) },
    { label: "Total", value: qty(line.total), strong: true },
  ];
}

/** Prix et coûts : seulement ce que la vue du rôle contient (le vendeur n'a aucun coût). */
function priceFacts(line: StockLine): Fact[] {
  const facts: Fact[] = [];
  const basePrice = basePriceOf(line);
  if (basePrice !== undefined)
    facts.push({ label: "Prix de base", value: moneyOr(basePrice, NOT_SET) });
  const costs = costsOf(line);
  if (costs !== null) {
    facts.push(
      { label: "Dernier coût", value: moneyOr(costs.lastCost, NOT_COMPUTABLE) },
      { label: "Coût moyen (CMP)", value: moneyOr(costs.wac, NOT_COMPUTABLE) },
      { label: "Valeur au CMP", value: moneyOr(costs.value, NOT_COMPUTABLE) },
    );
  }
  return facts;
}

/**
 * Un article de la matrice (UC-STK-05) en carte : à 360 px, une table article × lieux ne
 * tient pas ; la carte garde les colonnes de la matrice sous forme de liste, sans défilement.
 */
export function StockCard({
  line,
  onHistory,
}: {
  line: StockLine;
  /** Propriétaire et comptable : ouvre l'historique (UC-STK-06). */
  onHistory?: () => void;
}) {
  return (
    <li className="flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="m-0 min-w-0 break-words text-lead font-semibold text-text">{line.name}</h2>
        <StockBadge status={line.status} />
      </div>
      <Facts facts={quantityFacts(line)} />
      {priceFacts(line).length > 0 && <Facts facts={priceFacts(line)} />}
      {onHistory !== undefined && (
        <Button variant="secondary" fullWidth icon={History} onClick={onHistory}>
          {`Historique de ${line.name}`}
        </Button>
      )}
    </li>
  );
}
