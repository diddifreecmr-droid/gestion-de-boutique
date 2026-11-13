import type { Role } from "../../core/auth/me";
import { AppGatewaysProvider } from "../../core/gateways/GatewaysProvider";
import type { ExchangeRules } from "../../core/profile/types";
import { SalesPage } from "./SalesPage";
import { saleRole } from "./salesNav";

export interface SalesRouteProps {
  shopId: string;
  role: Role;
  title: string;
  /** Règles d'échange du profil servi (`useActiveShop().profile.exchange`). */
  exchange: ExchangeRules;
}

/** Entrée de route « Ventes » / « Mes ventes » (chargée à la demande). */
export default function SalesRoute(props: SalesRouteProps) {
  return (
    <AppGatewaysProvider>
      <SalesPage
        shopId={props.shopId}
        role={saleRole(props.role)}
        title={props.title}
        exchange={props.exchange}
      />
    </AppGatewaysProvider>
  );
}
