import { useMemo } from "react";
import type { Role } from "../../core/auth/me";
import { appCatalogAdmin, CatalogAdminContext } from "../../core/gateways/catalogAdminContext";
import { createHttpPurchasing, PurchasingContext } from "../../core/gateways/httpPurchasing";
import { useServices } from "../../core/services/servicesContext";
import { PurchasingPage } from "./PurchasingPage";
import { purchaseRole } from "./purchasingNav";

/**
 * Entrée de route « Achats » (chargée à la demande) : passerelles réelles des achats et du
 * catalogue (recherche et création d'article depuis la saisie), horloge de l'appareil.
 */
export default function PurchasingRoute({ shopId, role }: { shopId: string; role: Role }) {
  const services = useServices();
  const deps = useMemo(
    () => ({
      gateway: createHttpPurchasing(services),
      catalog: appCatalogAdmin(services),
      now: () => new Date(),
    }),
    [services],
  );
  return (
    <PurchasingContext.Provider value={deps}>
      <CatalogAdminContext.Provider value={deps.catalog}>
        <PurchasingPage shopId={shopId} role={purchaseRole(role)} />
      </CatalogAdminContext.Provider>
    </PurchasingContext.Provider>
  );
}
