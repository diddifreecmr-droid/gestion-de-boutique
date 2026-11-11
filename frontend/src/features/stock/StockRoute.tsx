import { useMemo } from "react";
import { useSearchParams } from "react-router";
import type { Role } from "../../core/auth/me";
import { createHttpStock, StockContext } from "../../core/gateways/httpStock";
import { useServices } from "../../core/services/servicesContext";
import CatalogRoute from "../catalog/CatalogRoute";
import { ARTICLE_PARAM } from "../catalog/catalogPaths";
import { AdjustmentPage } from "./AdjustmentPage";
import { DamagedPage } from "./DamagedPage";
import { InventoryPage } from "./InventoryPage";
import { InventoryStartPage } from "./InventoryStartPage";
import { MovementsPage } from "./MovementsPage";
import { ID_PARAM, VIEW, VIEW_PARAM } from "./stockNav";
import { StockMatrixPage } from "./StockMatrixPage";
import { isManager, stockRole, type ManagerRole, type StockRole } from "./stockRoles";
import { StockTabs } from "./StockTabs";
import { StockValuePage } from "./StockValuePage";

/**
 * Entrée de route (chargée à la demande) de la section « Stock » : passerelle réelle branchée
 * sur les services de l'application, puis l'écran désigné par l'adresse (`stockNav.ts`).
 */
export default function StockRoute({ shopId, role }: { shopId: string; role: Role }) {
  const services = useServices();
  const gateway = useMemo(() => createHttpStock(services), [services]);
  return (
    <StockContext.Provider value={gateway}>
      <StockScreen shopId={shopId} role={stockRole(role)} />
    </StockContext.Provider>
  );
}

function StockScreen({ shopId, role }: { shopId: string; role: StockRole }) {
  const [params] = useSearchParams();
  if (!isManager(role)) return <StockMatrixPage shopId={shopId} role={role} />;
  // La fiche et la création d'un article gardent les adresses du catalogue (`?article=`).
  if (params.get(ARTICLE_PARAM) !== null) return <CatalogRoute shopId={shopId} role={role} />;
  const view = params.get(VIEW_PARAM);
  if (view === VIEW.articles) {
    return (
      <>
        <StockTabs shopId={shopId} active="articles" />
        <CatalogRoute shopId={shopId} role={role} />
      </>
    );
  }
  const screen = managerScreen(shopId, role, view, params.get(ID_PARAM));
  if (screen !== null) return screen;
  return (
    <>
      <StockTabs shopId={shopId} active="stock" />
      <StockMatrixPage shopId={shopId} role={role} />
    </>
  );
}

/** Écrans réservés au propriétaire et au comptable ; `null` = la matrice. */
function managerScreen(shopId: string, role: ManagerRole, view: string | null, id: string | null) {
  switch (view) {
    case VIEW.movements:
      return id === null ? null : (
        <MovementsPage key={id} shopId={shopId} role={role} articleId={id} />
      );
    case VIEW.adjustment:
      return <AdjustmentPage key={id ?? "new"} shopId={shopId} articleId={id} />;
    case VIEW.inventory:
      return id === null ? (
        <InventoryStartPage shopId={shopId} />
      ) : (
        <InventoryPage key={id} shopId={shopId} inventoryId={id} />
      );
    case VIEW.value:
      return <StockValuePage shopId={shopId} />;
    case VIEW.damaged:
      return <DamagedPage shopId={shopId} />;
    default:
      return null;
  }
}
