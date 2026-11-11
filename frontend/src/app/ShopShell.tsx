import { Outlet, useNavigate, useParams } from "react-router";
import { activeNavKey, navItems, profileForShop, shopPath } from "../core/profile/shopProfile";
import { useSignedIn } from "../core/services/servicesContext";
import { BottomNav, TopBar } from "../shared/ui";
import { AppBanners } from "./AppBanners";
import { NotFoundPage } from "./NotFoundPage";
import { SHOP_PICKER_PATH } from "./paths";
import type { ActiveShop } from "./shopContext";

/**
 * Coquille d'une boutique (`/s/{shopId}/…`) : barre du haut (nom de la boutique, qui ouvre la
 * liste s'il y en a plusieurs — UC-SOC-03), bannières, page, barre du bas selon le rôle.
 */
export function ShopShell() {
  const me = useSignedIn();
  const navigate = useNavigate();
  const { shopId = "", section = "" } = useParams();
  const membership = me.shops.find((shop) => shop.shopId === shopId);
  if (membership === undefined) return <NotFoundPage />;

  const profile = profileForShop(shopId);
  const active: ActiveShop = {
    shopId,
    shopName: membership.shopName,
    role: membership.role,
    profile,
  };
  const items = navItems(profile, membership.role, shopId);
  return (
    <div className="min-h-screen pb-24">
      <TopBar
        title={membership.shopName}
        {...(me.shops.length > 1 ? { onTitleClick: () => void navigate(SHOP_PICKER_PATH) } : {})}
        alertCount={0}
        onAlertsClick={() => void navigate(shopPath(shopId, "alertes"))}
      />
      <AppBanners />
      <main className="mx-auto flex w-full max-w-150 flex-col gap-4 p-4">
        <Outlet context={active} />
      </main>
      <BottomNav
        items={items}
        activeKey={activeNavKey(profile, membership.role, section)}
        onNavigate={(item, event) => {
          event.preventDefault();
          void navigate(item.href);
        }}
      />
    </div>
  );
}
