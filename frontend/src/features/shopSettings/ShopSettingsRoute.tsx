import { useMemo } from "react";
import type { Role } from "../../core/auth/me";
import { createHttpShopAdmin, ShopAdminContext } from "../../core/gateways/httpShopAdmin";
import { useServices } from "../../core/services/servicesContext";
import { ShopSettingsPage } from "./ShopSettingsPage";

/**
 * Entrée de route « Réglages » (chargée à la demande) : passerelle réelle branchée sur les
 * services de l'application.
 */
export default function ShopSettingsRoute({
  shopId,
  role,
  title,
}: {
  shopId: string;
  role: Role;
  title: string;
}) {
  const services = useServices();
  const gateway = useMemo(() => createHttpShopAdmin(services), [services]);
  return (
    <ShopAdminContext.Provider value={gateway}>
      <ShopSettingsPage shopId={shopId} role={role} title={title} />
    </ShopAdminContext.Provider>
  );
}
