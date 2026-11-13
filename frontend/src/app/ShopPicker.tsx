import { useNavigate } from "react-router";
import type { ShopMembership } from "../core/auth/me";
import { savedProfile } from "../core/profile/savedProfiles";
import { shopPath } from "../core/profile/shopProfile";
import { useSignedIn } from "../core/services/servicesContext";
import { ListCard, ListCardRow } from "../shared/ui";

/**
 * Libellé du rôle (« Vendeur » ou « Employé ») : il dépend du profil de chaque boutique, que
 * `GET /me` ne donne pas. Seul le profil déjà lu sur cet appareil le fournit ; sinon, rien
 * plutôt qu'un libellé deviné.
 */
function roleSubtitle(shop: ShopMembership): { subtitle: string } | Record<string, never> {
  const label = savedProfile(shop.shopId, shop.role)?.role_label;
  return typeof label === "string" ? { subtitle: label } : {};
}

/** UC-SOC-03 — Choisir la boutique active ; ensuite tout l'écran ne montre qu'elle. */
export function ShopPicker() {
  const me = useSignedIn();
  const navigate = useNavigate();
  return (
    <main className="mx-auto flex w-full max-w-150 flex-col gap-4 p-4">
      <h1 className="m-0 text-title font-bold text-text">Choisir une boutique</h1>
      <ListCard label="Vos boutiques">
        {me.shops.map((shop) => (
          <ListCardRow
            key={shop.shopId}
            title={shop.shopName}
            {...roleSubtitle(shop)}
            onOpen={() => void navigate(shopPath(shop.shopId))}
          />
        ))}
      </ListCard>
    </main>
  );
}
