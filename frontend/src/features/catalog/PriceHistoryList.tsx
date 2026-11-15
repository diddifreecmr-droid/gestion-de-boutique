import type { PriceHistoryResponse } from "../../core/gateways/catalogAdminContract";
import { useActivePieceWords } from "../../core/profile/activeProfile";
import type { PieceWords } from "../../core/profile/pieceWords";
import { formatDate, formatTime } from "../../shared/format";
import { EmptyState } from "../../shared/ui";
import { FactsCard } from "./FactsCard";
import { moneyOr } from "./money";

/** « Prix de base au rouleau » : le mot de la pièce vient du profil (2026-11-15). */
function kindLabel(kind: string, words: PieceWords): string {
  if (kind === "base_price") return "Prix de base";
  if (kind === "min_price") return "Prix minimum";
  if (kind === "base_price_piece") return `Prix de base ${words.per}`;
  if (kind === "min_price_piece") return `Prix minimum ${words.per}`;
  throw new Error(`Type de prix inconnu dans l'historique : « ${kind} »`);
}

/** Historique des prix (UC-STK-03 : date, ancien prix, nouveau prix), le plus récent d'abord. */
export function PriceHistoryList({ history }: { history: readonly PriceHistoryResponse[] }) {
  const words = useActivePieceWords();
  if (history.length === 0)
    return <EmptyState message="Aucun changement de prix pour l'instant." />;
  const ordered = [...history].sort((a, b) => b.effective_at.localeCompare(a.effective_at));
  return (
    <FactsCard
      title="Historique des prix"
      facts={ordered.map((entry) => ({
        label: `${formatDate(entry.effective_at)} à ${formatTime(entry.effective_at)} — ${kindLabel(entry.price_kind, words)}`,
        value: `${moneyOr(entry.old_price, "aucun")} → ${moneyOr(entry.new_price, "retiré")}`,
      }))}
    />
  );
}
