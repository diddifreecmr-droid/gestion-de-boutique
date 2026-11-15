import type { StockStatus } from "../../core/gateways/catalogContract";
import { Badge, type BadgeStatus } from "../../shared/ui";

/** Pastille de stock de l'employé (2026-11-15) : couleur + mot + icône, jamais de chiffre. */
const STATUS: Record<StockStatus, { status: BadgeStatus; word: string }> = {
  ok: { status: "success", word: "En stock" },
  low: { status: "warning", word: "Stock bas" },
  out: { status: "danger", word: "Rupture" },
};

export function StockStatusBadge({ status }: { status: StockStatus }) {
  const { status: badge, word } = STATUS[status];
  return <Badge status={badge}>{word}</Badge>;
}
