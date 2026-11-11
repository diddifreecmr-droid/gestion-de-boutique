import { lazy, Suspense } from "react";
import { CirclePlus, UserRound, Wallet } from "lucide-react";
import { useNavigate } from "react-router";
import { shopPath } from "../core/profile/shopProfile";
import { useSignedIn } from "../core/services/servicesContext";
import { SALE_ROLES } from "../features/sales/saleRoles";
import { NEW_SALE_KEY } from "../features/sales/salesNav";
import { PAY_SEARCH, RECEIVABLES_KEY } from "../features/receivables/receivablesNav";
import { Button, EmptyState } from "../shared/ui";
import { useActiveShop } from "./shopContext";

export const ACCOUNT_KEY = "compte";

/** Alertes en attente du propriétaire (UC-TDB-01 point 6), chargées à la demande. */
const PriceRequestsHomeCard = lazy(
  () => import("../features/sales/priceRequests/PriceRequestsHomeCard"),
);

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
      {SALE_ROLES.includes(role) && (
        <Button
          size="lg"
          fullWidth
          icon={CirclePlus}
          onClick={() => void navigate(shopPath(shopId, NEW_SALE_KEY))}
        >
          Nouvelle vente
        </Button>
      )}
      {role === "seller" && (
        <Button
          variant="secondary"
          size="lg"
          fullWidth
          icon={Wallet}
          onClick={() => void navigate(`${shopPath(shopId, RECEIVABLES_KEY)}${PAY_SEARCH}`)}
        >
          Versement
        </Button>
      )}
      {role === "owner" && (
        <Suspense fallback={null}>
          <PriceRequestsHomeCard shopId={shopId} />
        </Suspense>
      )}
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
