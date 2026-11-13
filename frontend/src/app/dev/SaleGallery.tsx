import { useState } from "react";
import { createSimulatedGateways } from "../../core/gateways/simulated";
import { GatewaysProvider } from "../../core/gateways/GatewaysProvider";
import { ALL_MODULES, shopModules } from "../../core/profile/modules";
import { ModulesContext } from "../../core/profile/modulesContext";
import { NewSalePage } from "../../features/sales/NewSalePage";
import { GallerySection } from "./GallerySection";

/** Vitrine : boutique avec tous ses modules. */
const EVERY_MODULE = shopModules(ALL_MODULES);

/** Écran « Nouvelle vente » (§ 7.1) sur la passerelle simulée, rôle vendeur. */
export function SaleGallery() {
  const [gateways] = useState(() =>
    createSimulatedGateways({ isOnline: () => true, roleIn: () => "seller" }),
  );
  return (
    <GallerySection title="Écran : Nouvelle vente (passerelle simulée, vendeur)">
      <div className="mx-auto flex w-full max-w-150 flex-col gap-4 rounded-lg border border-border p-4">
        <ModulesContext.Provider value={EVERY_MODULE}>
          <GatewaysProvider gateways={gateways}>
            <NewSalePage shopId="vitrine" role="seller" />
          </GatewaysProvider>
        </ModulesContext.Provider>
      </div>
    </GallerySection>
  );
}
