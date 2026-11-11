import { useStockGateway } from "../../core/gateways/httpStock";
import { EmptyState } from "../../shared/ui";
import { InventoryCounting } from "./InventoryCounting";
import { InventoryResult } from "./InventoryResult";
import { BackButton, LoadPending, ScreenTitle } from "./Notice";
import { useStockNav } from "./stockNav";
import { useLoad } from "./useLoad";

/**
 * Un inventaire (UC-STK-07) selon son état : en cours → comptage (reprise possible), validé →
 * écarts, abandonné → message. L'adresse (`?vue=inventaire&id=…`) permet de revenir plus tard.
 */
export function InventoryPage({ shopId, inventoryId }: { shopId: string; inventoryId: string }) {
  const gateway = useStockGateway();
  const nav = useStockNav();
  const { load, replace, retry } = useLoad(`${shopId}|${inventoryId}`, () =>
    gateway.inventory(shopId, inventoryId),
  );
  const back = <BackButton label="Retour au stock" onClick={nav.matrix} />;
  if (load.status !== "ready") {
    return (
      <>
        {back}
        <ScreenTitle>Inventaire</ScreenTitle>
        <LoadPending load={load} label="Chargement de l'inventaire…" onRetry={retry} />
      </>
    );
  }
  const inventory = load.value;
  const title = `Inventaire ${inventory.number} — ${inventory.location_name}`;
  switch (inventory.status) {
    case "in_progress":
      return (
        <>
          {back}
          <ScreenTitle>{title}</ScreenTitle>
          <InventoryCounting
            key={inventory.id}
            shopId={shopId}
            inventory={inventory}
            onSaved={replace}
            onReload={retry}
            onAbandoned={() => {
              nav.inventory(undefined, true);
            }}
          />
        </>
      );
    case "validated":
      return (
        <>
          {back}
          <ScreenTitle>{title}</ScreenTitle>
          <InventoryResult inventory={inventory} />
        </>
      );
    case "abandoned":
      return (
        <>
          {back}
          <ScreenTitle>{title}</ScreenTitle>
          <EmptyState message="Cet inventaire a été abandonné : le stock n'a pas changé." />
        </>
      );
    default:
      throw new Error(`État d'inventaire inconnu : « ${inventory.status} »`);
  }
}
