import type { Role } from "../../core/auth/me";
import { AppGatewaysProvider } from "../../core/gateways/GatewaysProvider";
import { NewSalePage } from "./NewSalePage";

/** Entrée de route (chargée à la demande) : l'écran et les passerelles de l'application. */
export default function NewSaleRoute({ shopId, role }: { shopId: string; role: Role }) {
  return (
    <AppGatewaysProvider>
      <NewSalePage shopId={shopId} role={role} />
    </AppGatewaysProvider>
  );
}
