import { useSearchParams } from "react-router";
import type { Role } from "../../core/auth/me";
import { MembersScreen } from "./members/MembersScreen";
import { LocationsScreen } from "./places/LocationsScreen";
import { PaymentModesScreen } from "./places/PaymentModesScreen";
import { SETTINGS_ROLES } from "./settingsRights";
import { VIEW, type SettingsView } from "./settingsNav";
import { SettingsHub } from "./SettingsHub";
import { ShopSettingsScreen } from "./shop/ShopSettingsScreen";

export interface ShopSettingsPageProps {
  shopId: string;
  role: Role;
  title: string;
  accountPath: string;
}

/**
 * Section « Réglages » (UC-SOC-04 à 06) : sommaire, membres, lieux, modes de paiement,
 * réglages de la boutique. Propriétaire seulement (CDC § 4.2 « Gérer les utilisateurs et les
 * réglages de la boutique ») : la garde de route ne l'ouvre qu'à lui.
 */
export function ShopSettingsPage({ shopId, role, title, accountPath }: ShopSettingsPageProps) {
  if (!SETTINGS_ROLES.includes(role)) {
    throw new Error(`Le rôle « ${role} » n'accède pas aux réglages (garde de route manquante)`);
  }
  const [params, setParams] = useSearchParams();
  const view = params.get("vue");
  const common = {
    shopId,
    onBack: () => {
      setParams({});
    },
  };
  const open = (target: SettingsView) => {
    setParams({ vue: target });
  };

  switch (view) {
    case VIEW.members:
      return <MembersScreen {...common} />;
    case VIEW.locations:
      return <LocationsScreen {...common} />;
    case VIEW.paymentModes:
      return <PaymentModesScreen {...common} />;
    case VIEW.shop:
      return <ShopSettingsScreen {...common} />;
    default:
      return <SettingsHub title={title} accountPath={accountPath} onOpen={open} />;
  }
}
