import { History } from "lucide-react";
import { useModules } from "../../core/profile/modulesContext";
import { Button, ListCardDetailRow } from "../../shared/ui";
import { moneyOr, NOT_COMPUTABLE, NOT_SET } from "../catalog/money";
import { Facts, type Fact } from "./Facts";
import { StockBadge } from "./Notice";
import { isZero, quantityText } from "./quantities";
import { basePriceOf, costsOf, type StockLine } from "./stockView";

/**
 * Quantités : un lieu par ligne (ordre des lieux), « En route », puis « Total ». « En route »
 * vient des déplacements (module `transfers`) : sans le module, la ligne n'apparaît que si une
 * quantité est réellement en route (données gardées), pour que le total reste expliqué.
 */
function quantityFacts(line: StockLine, transfers: boolean): Fact[] {
  const qty = (value: string) => quantityText(value, line.unit);
  const places = line.places.map((place) => ({
    label: place.name,
    value: isZero(place.damaged)
      ? qty(place.sellable)
      : `${qty(place.sellable)} (+ ${qty(place.damaged)} abîmé)`,
  }));
  const incoming =
    transfers || !isZero(line.incoming) ? [{ label: "En route", value: qty(line.incoming) }] : [];
  return [...places, ...incoming, { label: "Total", value: qty(line.total), strong: true }];
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
 * Un article de la matrice (UC-STK-05, audit UX du 13/11/2026) : sur la ligne, le nom, la
 * quantité totale et la pastille (Rupture, Stock bas) ; un appui déplie le détail — stock par
 * lieu, prix et coûts selon le rôle, historique. Aucun prix ni coût sur la ligne elle-même.
 */
export function StockItem({
  line,
  onHistory,
}: {
  line: StockLine;
  /** Propriétaire et comptable : ouvre l'historique (UC-STK-06). */
  onHistory?: () => void;
}) {
  const transfers = useModules().has("transfers");
  const prices = priceFacts(line);
  return (
    <ListCardDetailRow
      title={line.name}
      value={quantityText(line.total, line.unit)}
      valueLabel="En stock"
      badge={<StockBadge status={line.status} />}
    >
      <Facts facts={quantityFacts(line, transfers)} />
      {prices.length > 0 && <Facts facts={prices} />}
      {onHistory !== undefined && (
        <Button variant="secondary" fullWidth icon={History} onClick={onHistory}>
          {`Historique de ${line.name}`}
        </Button>
      )}
    </ListCardDetailRow>
  );
}
