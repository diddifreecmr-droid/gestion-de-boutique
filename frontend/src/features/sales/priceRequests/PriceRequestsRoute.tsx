import { AppGatewaysProvider } from "../../../core/gateways/GatewaysProvider";
import { PriceRequestsPage } from "./PriceRequestsPage";

/** Entrée de route « Demandes de prix » du propriétaire (chargée à la demande). */
export default function PriceRequestsRoute({ shopId }: { shopId: string }) {
  return (
    <AppGatewaysProvider>
      <PriceRequestsPage shopId={shopId} />
    </AppGatewaysProvider>
  );
}
