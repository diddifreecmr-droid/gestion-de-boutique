import type { Role } from "../../core/auth/me";
import { AccountantHome } from "./AccountantHome";
import { DriverHome } from "./DriverHome";
import { ReportingProvider } from "./ReportingProvider";
import { SalesHome } from "./SalesHome";

function RoleScreen({ shopId, role }: { shopId: string; role: Role }) {
  switch (role) {
    case "owner":
    case "seller":
      return <SalesHome shopId={shopId} role={role} />;
    case "accountant":
      return <AccountantHome shopId={shopId} />;
    case "driver":
      return <DriverHome shopId={shopId} />;
  }
}

/**
 * Entrée de route de l'accueil (chargée à la demande, specs § 4.6) : page minimale de vente
 * pour le propriétaire et le vendeur (specs § 15.1), accueil simple du comptable et du
 * chauffeur. Le tableau de bord complet est un écran à part (`DashboardRoute`).
 */
export default function HomeRoute({ shopId, role }: { shopId: string; role: Role }) {
  return (
    <ReportingProvider>
      <RoleScreen shopId={shopId} role={role} />
    </ReportingProvider>
  );
}
