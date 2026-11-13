import { useNavigate } from "react-router";
import { useActiveProfile } from "../../core/profile/activeProfile";
import { shopPath } from "../../core/profile/shopProfile";
import { roleWord } from "../../core/profile/vocabulary";
import { Badge, ListCard, ListCardRow } from "../../shared/ui";
import PriceRequestsHomeCard from "../sales/priceRequests/PriceRequestsHomeCard";
import { SALES_KEY } from "../sales/salesNav";
import { count } from "./homeText";
import { Section } from "./Section";

/**
 * UC-TDB-01 point 6 : erreurs signalées par les vendeurs (traitées sur la fiche de la vente,
 * depuis « Ventes ») et demandes de prix sous le minimum (carte existante, relue toutes les
 * 10 s). `errorReports` : le nombre, ou la phrase qui le remplace (lecture, hors connexion).
 * Dans le tableau de bord, elle reste ouverte (repliable) : une demande de prix en attente ne
 * doit pas se cacher derrière un appui.
 */
export function AlertsSection({
  shopId,
  errorReports,
}: {
  shopId: string;
  errorReports: number | string;
}) {
  const navigate = useNavigate();
  const profile = useActiveProfile();
  const subtitle =
    typeof errorReports === "string"
      ? errorReports
      : count(errorReports, "erreur à traiter", "erreurs à traiter", "Aucune erreur signalée");
  return (
    <Section title="Alertes en attente" defaultOpen>
      <ListCard label="Erreurs signalées">
        <ListCardRow
          title={`Erreurs signalées par les ${roleWord(profile.roleLabel, "seller", true)}`}
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
