import type { Role } from "../../core/auth/me";
import { AppGatewaysProvider } from "../../core/gateways/GatewaysProvider";
import { SalesPage } from "./SalesPage";
import { saleRole } from "./salesNav";

/** Entrée de route « Ventes » / « Mes ventes » (chargée à la demande). */
export default function SalesRoute(props: { shopId: string; role: Role; title: string }) {
  return (
    <AppGatewaysProvider>
      <SalesPage shopId={props.shopId} role={saleRole(props.role)} title={props.title} />
    </AppGatewaysProvider>
  );
}
