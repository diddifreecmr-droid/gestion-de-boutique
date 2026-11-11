import { lazy, Suspense } from "react";
import { UserRound } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router";
import { shopPath } from "../core/profile/shopProfile";
import { useSignedIn } from "../core/services/servicesContext";
import { DETAIL_PARAM } from "../features/dashboard/dashboardNav";
import { Button, Skeleton } from "../shared/ui";
import { useActiveShop } from "./shopContext";

export const ACCOUNT_KEY = "compte";

/** Accueils par rôle et tableau de bord (module 14, T22), chargés à la demande. */
const HomeRoute = lazy(() => import("../features/dashboard/HomeRoute"));

/**
 * Accueil de la boutique (UC-TDB-01 à 05) : titre et salutation, puis l'accueil du rôle ; le
 * détail d'un chiffre du propriétaire (`?detail=…`) occupe tout l'écran. « Mon compte » reste
 * accessible depuis l'accueil (design-system § 6.6).
 */
export function RoleHome() {
  const me = useSignedIn();
  const { shopId, role, profile } = useActiveShop();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [home] = profile.menu(role);
  const content = (
    <Suspense fallback={<Skeleton lines={4} label="Ouverture de l'accueil…" />}>
      <HomeRoute shopId={shopId} role={role} />
    </Suspense>
  );
  if (role === "owner" && params.has(DETAIL_PARAM)) return content;
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">{home?.label ?? "Accueil"}</h1>
      <p className="m-0 text-lead text-text">
        Bonjour {me.name} — {profile.roleLabel(role)}
      </p>
      {content}
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
