import { Badge } from "../../shared/ui";
import { statusOf } from "./labels";

/** Pastille du statut d'une créance : mot + icône, jamais la couleur seule (P7). */
export function StatusBadge({ status }: { status: string }) {
  const { label, badge } = statusOf(status);
  return <Badge status={badge}>{label}</Badge>;
}
