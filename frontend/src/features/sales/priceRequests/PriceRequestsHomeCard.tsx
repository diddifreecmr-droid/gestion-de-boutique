import { useNavigate } from "react-router";
import { AppGatewaysProvider } from "../../../core/gateways/GatewaysProvider";
import { shopPath } from "../../../core/profile/shopProfile";
import { ListCard, ListCardRow, Badge } from "../../../shared/ui";
import { PRICE_REQUESTS_KEY } from "../salesNav";
import { usePendingRequests } from "./usePendingRequests";

function Entry({ shopId }: { shopId: string }) {
  const navigate = useNavigate();
  const { state } = usePendingRequests(shopId, false);
  const count = state.status === "ready" ? state.items.length : null;
  const subtitle =
    state.status === "loading"
      ? "Lecture…"
      : count === null
        ? "Nombre disponible avec internet"
        : count === 0
          ? "Aucune demande en attente"
          : `${String(count)} en attente de votre réponse`;
  return (
    <ListCard label="Alertes en attente">
      <ListCardRow
        title="Demandes de prix sous le minimum"
        subtitle={subtitle}
        {...(count !== null && count > 0
          ? { badge: <Badge status="warning">À valider</Badge> }
          : {})}
        onOpen={() => void navigate(shopPath(shopId, PRICE_REQUESTS_KEY))}
      />
    </ListCard>
  );
}

/**
 * Carte « Alertes en attente » de l'accueil du propriétaire (UC-TDB-01 point 6) : nombre de
 * demandes de prix en attente, relu toutes les 10 s ; un appui ouvre la liste.
 */
export default function PriceRequestsHomeCard({ shopId }: { shopId: string }) {
  return (
    <AppGatewaysProvider>
      <Entry shopId={shopId} />
    </AppGatewaysProvider>
  );
}
