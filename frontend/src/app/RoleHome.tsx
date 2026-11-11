import { UserRound } from "lucide-react";
import { useNavigate } from "react-router";
import { shopPath } from "../core/profile/shopProfile";
import { useSignedIn } from "../core/services/servicesContext";
import { Button, EmptyState } from "../shared/ui";
import { useActiveShop } from "./shopContext";

export const ACCOUNT_KEY = "compte";

/** PROVISOIRE (T12) — accueil du rôle ; le contenu réel (module 14) arrive avec T19 / T22. */
export function RoleHome() {
  const me = useSignedIn();
  const { shopId, role, profile } = useActiveShop();
  const navigate = useNavigate();
  const [home] = profile.menu(role);
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">{home?.label ?? "Accueil"}</h1>
      <p className="m-0 text-lead text-text">
        Bonjour {me.name} — {profile.roleLabel(role)}
      </p>
      <EmptyState message="Votre accueil arrive bientôt." />
      <Button
        variant="secondary"
        fullWidth
        icon={UserRound}
        onClick={() => void navigate(shopPath(shopId, ACCOUNT_KEY))}
      >
        Mon compte
      </Button>
    </>
  );
}
