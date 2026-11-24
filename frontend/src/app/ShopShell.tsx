import type { ReactNode } from "react";
import { Outlet, useNavigate, useParams } from "react-router";
import type { ShopMembership } from "../core/auth/me";
import { ModulesContext } from "../core/profile/modulesContext";
import { activeNavKey, navItems, shopPath } from "../core/profile/shopProfile";
import { ShopLogoContext } from "../core/profile/shopLogoContext";
import { useShopProfile } from "../core/profile/useShopProfile";
import { useSignedIn } from "../core/services/servicesContext";
import { BottomNav, EmptyState, ShopLogo, ShopWatermark, Skeleton, TopBar } from "../shared/ui";
import { AppBanners } from "./AppBanners";
import { NotFoundPage } from "./NotFoundPage";
import { SHOP_PICKER_PATH } from "./paths";
import { ACCOUNT_KEY } from "./RoleHome";
import type { ActiveShop } from "./shopContext";
import { useShopLogoState } from "./useShopLogoState";

/** Hors connexion, profil jamais lu sur cet appareil : rien n'est deviné. */
export const PROFILE_UNAVAILABLE =
  "Connexion nécessaire pour ouvrir cette boutique une première fois sur ce téléphone.";

/**
 * Coquille d'une boutique (`/s/{shopId}/…`) : barre du haut (logo et nom de la boutique, qui ouvre la
 * liste s'il y en a plusieurs — UC-SOC-03 ; cloche ; « Compte » pour tous les rôles, § 6.6),
 * bannières, page, barre du bas **servie par le profil** (`GET /profile`) selon le rôle et les
 * modules actifs (specs § 4.5, § 15.1). Le logo (ou le logo générique) est aussi en filigrane
 * très pâle au fond de l'écran (décision client du 2026-11-24).
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
  const state = useShopProfile(shopId, role);
  const logo = useShopLogoState(state.status === "ready" ? state.profile.logoPath : null);
  const name = membership.shopName;

  const frame = (content: ReactNode, nav?: ReactNode) => (
    <div className="relative isolate min-h-screen pb-24">
      <ShopWatermark name={name} src={logo.src} />
      <TopBar
        title={name}
        logo={<ShopLogo name={name} src={logo.src} />}
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

  // Ni barre du haut ni barre du bas avant de connaître le profil : rien d'éteint n'apparaît.
  if (state.status === "loading") {
    return (
      <main className="mx-auto flex w-full max-w-150 flex-col gap-4 p-4">
        <Skeleton lines={4} label="Ouverture de la boutique…" />
      </main>
    );
  }
  if (state.status === "unavailable") return frame(<EmptyState message={PROFILE_UNAVAILABLE} />);
  const { modules, profile } = state;
  const active: ActiveShop = { shopId, shopName: membership.shopName, role, profile };
  const items = navItems(profile, shopId);
  return (
    <ModulesContext.Provider value={modules}>
      <ShopLogoContext.Provider value={logo}>
        {frame(
          <Outlet context={active} />,
          // Un menu servi vide (ex. chauffeur sans module actif) : pas de barre du bas.
          items.length > 0 && (
            <BottomNav
              items={items}
              activeKey={activeNavKey(profile, section)}
              onNavigate={(item, event) => {
                event.preventDefault();
                void navigate(item.href);
              }}
            />
          ),
        )}
      </ShopLogoContext.Provider>
    </ModulesContext.Provider>
  );
}
