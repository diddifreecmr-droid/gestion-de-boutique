import { useStockGateway } from "../../core/gateways/httpStock";
import type { DamagedLine } from "../../core/gateways/stockContract";
import { EmptyState } from "../../shared/ui";
import { moneyOr, NOT_COMPUTABLE } from "../catalog/money";
import { Facts, type Fact } from "./Facts";
import { BackButton, LoadPending, ScreenTitle } from "./Notice";
import { quantityText } from "./quantities";
import { useStockNav } from "./stockNav";
import { useLoad } from "./useLoad";

function facts(line: DamagedLine): Fact[] {
  const list: Fact[] = [
    { label: "Lieu", value: line.location_name },
    { label: "Quantité abîmée", value: quantityText(line.damaged, line.stock_unit) },
  ];
  // Coûts posés seulement pour qui les voit (TR-05) ; `null` = CMP inconnu.
  if (line.wac_value !== undefined) {
    list.push({ label: "Valeur au CMP", value: moneyOr(line.wac_value, NOT_COMPUTABLE) });
  }
  return list;
}

/** Stock abîmé (propriétaire et comptable) : un article par lieu, quantité et valeur au CMP. */
export function DamagedPage({ shopId }: { shopId: string }) {
  const gateway = useStockGateway();
  const nav = useStockNav();
  const { load, retry } = useLoad(`${shopId}|damaged`, () => gateway.damaged(shopId));
  return (
    <>
      <BackButton label="Retour au stock" onClick={nav.matrix} />
      <ScreenTitle>Stock abîmé</ScreenTitle>
      {load.status !== "ready" && (
        <LoadPending load={load} label="Chargement du stock abîmé…" onRetry={retry} />
      )}
      {load.status === "ready" && load.value.items.length === 0 && (
        <EmptyState message="Aucun stock abîmé." />
      )}
      {load.status === "ready" && load.value.items.length > 0 && (
        <ul aria-label="Stock abîmé" className="m-0 flex list-none flex-col gap-4 p-0">
          {load.value.items.map((line) => (
            <li
              key={`${line.article_id}|${line.location_id}`}
              className="flex flex-col gap-2 rounded-lg bg-surface p-4 shadow-card"
            >
              <h2 className="m-0 break-words text-lead font-semibold text-text">
                {line.display_name}
              </h2>
              <Facts facts={facts(line)} />
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
