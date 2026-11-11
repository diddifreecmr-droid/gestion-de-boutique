import type { PriceHistoryResponse } from "../../core/gateways/catalogAdminContract";
import { formatDate, formatTime } from "../../shared/format";
import { EmptyState } from "../../shared/ui";
import { FactsCard } from "./FactsCard";
import { moneyOr } from "./money";

const KIND_LABELS: Readonly<Record<string, string>> = {
  base_price: "Prix de base",
  min_price: "Prix minimum",
  base_price_piece: "Prix de base à la pièce",
  min_price_piece: "Prix minimum à la pièce",
};

function kindLabel(kind: string): string {
  const label = KIND_LABELS[kind];
  if (label === undefined) throw new Error(`Type de prix inconnu dans l'historique : « ${kind} »`);
  return label;
}

/** Historique des prix (UC-STK-03 : date, ancien prix, nouveau prix), le plus récent d'abord. */
export function PriceHistoryList({ history }: { history: readonly PriceHistoryResponse[] }) {
  if (history.length === 0)
    return <EmptyState message="Aucun changement de prix pour l'instant." />;
  const ordered = [...history].sort((a, b) => b.effective_at.localeCompare(a.effective_at));
  return (
    <FactsCard
      title="Historique des prix"
      facts={ordered.map((entry) => ({
        label: `${formatDate(entry.effective_at)} à ${formatTime(entry.effective_at)} — ${kindLabel(entry.price_kind)}`,
        value: `${moneyOr(entry.old_price, "aucun")} → ${moneyOr(entry.new_price, "retiré")}`,
      }))}
    />
  );
}
