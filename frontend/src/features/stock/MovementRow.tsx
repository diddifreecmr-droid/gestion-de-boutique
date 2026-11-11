import type { Movement } from "../../core/gateways/stockContract";
import { formatDate, formatTime } from "../../shared/format";
import { Badge } from "../../shared/ui";
import { Facts } from "./Facts";
import { documentLabel } from "./documents";
import { quantityText, signedQuantityText } from "./quantities";

/** Un mouvement de l'historique (UC-STK-06) : date, type, lieu, ±quantité, stock après… */
export function MovementRow({
  movement,
  unit,
  author,
}: {
  movement: Movement;
  unit: string;
  author: string;
}) {
  const place =
    movement.condition === "damaged" ? `${movement.location_name} (abîmé)` : movement.location_name;
  return (
    <li className="flex flex-col gap-2 px-4 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="min-w-0 break-words text-lead font-semibold text-text">
          {movement.type_label}
        </span>
        <span className="text-lead font-bold tabular-nums text-text">
          {signedQuantityText(movement.quantity, unit)}
        </span>
      </div>
      {movement.stock_to_verify && <Badge status="warning">Stock à vérifier</Badge>}
      <Facts
        facts={[
          {
            label: "Date",
            value: `${formatDate(movement.occurred_at)} à ${formatTime(movement.occurred_at)}`,
          },
          { label: "Lieu", value: place },
          { label: "Stock après", value: quantityText(movement.balance_after, unit) },
          { label: "Document", value: documentLabel(movement.document) },
          { label: "Auteur", value: author },
        ]}
      />
    </li>
  );
}
