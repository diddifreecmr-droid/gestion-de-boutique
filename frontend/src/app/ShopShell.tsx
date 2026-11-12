import type { ReactNode } from "react";
import { RefreshCw } from "lucide-react";
import { Outlet, useNavigate, useParams } from "react-router";
import type { ShopMembership } from "../core/auth/me";
import { ModulesContext } from "../core/profile/modulesContext";
import {
  activeNavKey,
  navItems,
  profileForShop,
  shopPath,
  withModules,
} from "../core/profile/shopProfile";
import { useShopModules } from "../core/profile/useShopModules";
import { useSignedIn } from "../core/services/servicesContext";
import { BottomNav, Button, EmptyState, Skeleton, TopBar } from "../shared/ui";
import { AppBanners } from "./AppBanners";
import { NotFoundPage } from "./NotFoundPage";
import { SHOP_PICKER_PATH } from "./paths";
import { ACCOUNT_KEY } from "./RoleHome";
import type { ActiveShop } from "./shopContext";

/**
 * Coquille d'une boutique (`/s/{shopId}/…`) : barre du haut (nom de la boutique, qui ouvre la
 * liste s'il y en a plusieurs — UC-SOC-03 ; cloche ; « Compte » pour tous les rôles, § 6.6),
 * bannières, page, barre du bas selon le rôle **et les modules actifs** (specs § 15.1).
 */
export function ShopShell() {
  const me = useSignedIn();
  const { shopId = "" } = useParams();
  const membership = me.shops.find((shop) => shop.shopId === shopId);
  if (membership === undefined) return <NotFoundPage />;
  return <ShopFrame key={shopId} membership={membership} several={me.shops.length > 1} />;
}

function ShopFrame({ membership, several }: { membership: ShopMembership; several: boolean }) {
  const navigate = useNavigate();
  const { section = "" } = useParams();
  const { shopId, role } = membership;
  const { state, retry } = useShopModules(shopId);

  const frame = (content: ReactNode, nav?: ReactNode) => (
    <div className="min-h-screen pb-24">
      <TopBar
        title={membership.shopName}
        {...(several ? { onTitleClick: () => void navigate(SHOP_PICKER_PATH) } : {})}
        alertCount={0}
        onAlertsClick={() => void navigate(shopPath(shopId, "alertes"))}
        onAccountClick={() => void navigate(shopPath(shopId, ACCOUNT_KEY))}
      />
      <AppBanners />
      <main className="mx-auto flex w-full max-w-150 flex-col gap-4 p-4">{content}</main>
      {nav}
    </div>
  );

  // Ni barre du haut ni barre du bas avant de connaître les modules : rien d'éteint n'apparaît.
  if (state.status === "loading") {
    return (
      <main className="mx-auto flex w-full max-w-150 flex-col gap-4 p-4">
        <Skeleton lines={4} label="Ouverture de la boutique…" />
      </main>
    );
  }
  if (state.status === "offline") {
    return frame(
      <EmptyState
        message="Connexion nécessaire pour ouvrir la boutique la première fois."
        action={
          <Button variant="secondary" icon={RefreshCw} onClick={retry}>
            Réessayer
          </Button>
        }
      />,
    );
  }
  const { modules } = state;
  const profile = withModules(profileForShop(shopId), modules);
  const active: ActiveShop = { shopId, shopName: membership.shopName, role, profile };
  return (
    <ModulesContext.Provider value={modules}>
      {frame(
        <Outlet context={active} />,
        <BottomNav
          items={navItems(profile, role, shopId)}
          activeKey={activeNavKey(profile, role, section)}
          onNavigate={(item, event) => {
            event.preventDefault();
            void navigate(item.href);
          }}
        />,
      )}
    </ModulesContext.Provider>
  );
}
