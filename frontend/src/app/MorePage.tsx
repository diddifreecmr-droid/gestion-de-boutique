import { UserRound } from "lucide-react";
import { useNavigate } from "react-router";
import { shopPath } from "../core/profile/shopProfile";
import { ActionTile, ActionTileGrid } from "../shared/ui";
import { ACCOUNT_KEY } from "./RoleHome";
import { useActiveShop } from "./shopContext";

/** Entrée « Plus » du propriétaire (CDC § 17.4) : le reste de ses écrans, en tuiles. */
export function MorePage() {
  const { shopId, role, profile } = useActiveShop();
  const navigate = useNavigate();
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Plus</h1>
      <ActionTileGrid>
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
