import { useState } from "react";
import type { ShopSettings } from "../../../core/gateways/shopAdminContract";
import { useShopAdmin } from "../../../core/gateways/httpShopAdmin";
import { useModules } from "../../../core/profile/modulesContext";
import { useLoad } from "../../expenses/useLoad";
import { ScreenFrame } from "../ScreenFrame";
import type { SettingsScreenProps } from "../settingsNav";
import { ExchangeSettingsSection } from "./ExchangeSettingsSection";
import { HeaderSection } from "./HeaderSection";
import { ReceiptSection } from "./ReceiptSection";
import { ReceptionSection } from "./ReceptionSection";
import { SalesRulesSection } from "./SalesRulesSection";

/**
 * Réglages de la boutique (UC-SOC-06, SET-01, SET-02) : prix et stock, échanges, reçu, en-tête,
 * réception des achats (module Achats actif seulement). Chaque groupe s'enregistre seul ; la réponse (nouvelle `version`)
 * remplace les réglages lus, pour que le groupe suivant ne soit pas refusé (409).
 */
export function ShopSettingsScreen({ shopId, onBack }: SettingsScreenProps) {
  const gateway = useShopAdmin();
  const purchases = useModules().has("purchases");
  const [round, setRound] = useState(0);
  const loaded = useLoad(`${shopId}:${String(round)}`, async () => {
    const [settings, locations] = await Promise.all([
      gateway.settings(shopId),
      gateway.locations(shopId),
    ]);
    return { settings, locations };
  });
  const [saved, setSaved] = useState<ShopSettings | null>(null);

  return (
    <ScreenFrame
      title="Réglages de la boutique"
      onBack={onBack}
      loaded={loaded}
      onRetry={() => {
        setRound((n) => n + 1);
      }}
    >
      {({ settings: initial, locations }) => {
        const common = { shopId, settings: saved ?? initial, onSaved: setSaved };
        return (
          <>
            <SalesRulesSection {...common} />
            <ExchangeSettingsSection {...common} />
            <ReceiptSection {...common} />
            <HeaderSection {...common} />
            {purchases && <ReceptionSection {...common} locations={locations} />}
          </>
        );
      }}
    </ScreenFrame>
  );
}
