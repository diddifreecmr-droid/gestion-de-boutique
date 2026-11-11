import { useNavigate } from "react-router";
import { profileForShop, shopPath } from "../core/profile/shopProfile";
import { useSignedIn } from "../core/services/servicesContext";
import { ListCard, ListCardRow } from "../shared/ui";

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
            subtitle={profileForShop(shop.shopId).roleLabel(shop.role)}
            onOpen={() => void navigate(shopPath(shop.shopId))}
          />
        ))}
      </ListCard>
    </main>
  );
}
