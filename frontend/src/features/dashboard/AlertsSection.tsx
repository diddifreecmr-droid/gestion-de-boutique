import { useNavigate } from "react-router";
import { shopPath } from "../../core/profile/shopProfile";
import { Badge, ListCard, ListCardRow } from "../../shared/ui";
import PriceRequestsHomeCard from "../sales/priceRequests/PriceRequestsHomeCard";
import { SALES_KEY } from "../sales/salesNav";
import { count } from "./homeText";
import { Section } from "./Section";

/**
 * UC-TDB-01 point 6 : erreurs signalées par les vendeurs (traitées sur la fiche de la vente,
 * depuis « Ventes ») et demandes de prix sous le minimum (carte existante, relue toutes les
 * 10 s). `errorReports` : le nombre, ou la phrase qui le remplace (lecture, hors connexion).
 */
export function AlertsSection({
  shopId,
  errorReports,
}: {
  shopId: string;
  errorReports: number | string;
}) {
  const navigate = useNavigate();
  const subtitle =
    typeof errorReports === "string"
      ? errorReports
      : count(errorReports, "erreur à traiter", "erreurs à traiter", "Aucune erreur signalée");
  return (
    <Section title="Alertes en attente">
      <ListCard label="Erreurs signalées">
        <ListCardRow
          title="Erreurs signalées par les vendeurs"
          subtitle={subtitle}
          {...(typeof errorReports === "number" && errorReports > 0
            ? { badge: <Badge status="warning">À traiter</Badge> }
            : {})}
          onOpen={() => void navigate(shopPath(shopId, SALES_KEY))}
        />
      </ListCard>
      <PriceRequestsHomeCard shopId={shopId} />
    </Section>
  );
}
