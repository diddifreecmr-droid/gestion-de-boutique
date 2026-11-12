import { LayoutDashboard, UserRound } from "lucide-react";
import { useNavigate } from "react-router";
import { shopPath } from "../core/profile/shopProfile";
import { useDashboardModule } from "../features/dashboard/dashboardModule";
import { DASHBOARD_KEY } from "../features/dashboard/dashboardNav";
import { ActionTile, ActionTileGrid } from "../shared/ui";
import { ACCOUNT_KEY } from "./RoleHome";
import { useActiveShop } from "./shopContext";

/** « Tableau de bord » : seulement si le module `dashboard` de la boutique est actif (§ 15.1). */
function DashboardTile({ shopId }: { shopId: string }) {
  const navigate = useNavigate();
  const { loaded } = useDashboardModule(shopId);
  if (loaded.status !== "ready" || !loaded.value) return null;
  return (
    <ActionTile
      icon={LayoutDashboard}
      label="Tableau de bord"
      onClick={() => void navigate(shopPath(shopId, DASHBOARD_KEY))}
    />
  );
}

/** Entrée « Plus » du propriétaire (CDC § 17.4) : le reste de ses écrans, en tuiles. */
export function MorePage() {
  const { shopId, role, profile } = useActiveShop();
  const navigate = useNavigate();
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Plus</h1>
      <ActionTileGrid>
        {role === "owner" && <DashboardTile shopId={shopId} />}
        {profile.more(role).map((entry) => (
          <ActionTile
            key={entry.key}
            icon={entry.icon}
            label={entry.label}
            onClick={() => void navigate(shopPath(shopId, entry.key))}
          />
        ))}
        <ActionTile
          icon={UserRound}
          label="Mon compte"
          onClick={() => void navigate(shopPath(shopId, ACCOUNT_KEY))}
        />
      </ActionTileGrid>
    </>
  );
}
