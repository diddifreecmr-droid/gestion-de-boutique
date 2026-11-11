import { useMemo } from "react";
import type { Role } from "../../core/auth/me";
import { createHttpReporting } from "../../core/gateways/httpReporting";
import { useServices } from "../../core/services/servicesContext";
import { AccountantHome } from "./AccountantHome";
import { useDashboardNav } from "./dashboardNav";
import { DetailPage } from "./DetailPage";
import { DriverHome } from "./DriverHome";
import { OwnerHome } from "./OwnerHome";
import { ReportingContext } from "./reportingContext";
import { SellerHome } from "./SellerHome";

function OwnerRoute({ shopId }: { shopId: string }) {
  const { metric } = useDashboardNav();
  return metric === null ? (
    <OwnerHome shopId={shopId} />
  ) : (
    <DetailPage shopId={shopId} metric={metric} />
  );
}

function RoleScreen({ shopId, role }: { shopId: string; role: Role }) {
  switch (role) {
    case "owner":
      return <OwnerRoute shopId={shopId} />;
    case "seller":
      return <SellerHome shopId={shopId} />;
    case "accountant":
      return <AccountantHome shopId={shopId} />;
    case "driver":
      return <DriverHome shopId={shopId} />;
  }
}

/**
 * Entrée de route de l'accueil (chargée à la demande, specs § 4.6) : passerelle réelle
 * branchée sur les services de l'application, horloge de l'appareil ; un accueil par rôle.
 */
export default function HomeRoute({ shopId, role }: { shopId: string; role: Role }) {
  const services = useServices();
  const deps = useMemo(
    () => ({ gateway: createHttpReporting(services), now: () => new Date() }),
    [services],
  );
  return (
    <ReportingContext.Provider value={deps}>
      <RoleScreen shopId={shopId} role={role} />
    </ReportingContext.Provider>
  );
}
