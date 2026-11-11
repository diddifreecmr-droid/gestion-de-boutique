import { useState } from "react";
import { createSimulatedGateways } from "../../core/gateways/gateways";
import { GatewaysProvider } from "../../core/gateways/GatewaysProvider";
import { NewSalePage } from "../../features/sales/NewSalePage";
import { GallerySection } from "./GallerySection";

/** Écran « Nouvelle vente » (§ 7.1) sur la passerelle simulée, rôle vendeur. */
export function SaleGallery() {
  const [gateways] = useState(() =>
    createSimulatedGateways({ isOnline: () => true, roleIn: () => "seller" }),
  );
  return (
    <GallerySection title="Écran : Nouvelle vente (passerelle simulée, vendeur)">
      <div className="mx-auto flex w-full max-w-150 flex-col gap-4 rounded-lg border border-border p-4">
        <GatewaysProvider gateways={gateways}>
          <NewSalePage shopId="vitrine" role="seller" />
        </GatewaysProvider>
      </div>
    </GallerySection>
  );
}
