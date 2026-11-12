import { useDashboardNav } from "./dashboardNav";
import { DetailPage } from "./DetailPage";
import { OwnerHome } from "./OwnerHome";
import { ReportingProvider } from "./ReportingProvider";

function DashboardScreen({ shopId }: { shopId: string }) {
  const { metric } = useDashboardNav();
  if (metric !== null) return <DetailPage shopId={shopId} metric={metric} />;
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Tableau de bord</h1>
      <OwnerHome shopId={shopId} />
    </>
  );
}

/**
 * Tableau de bord complet du propriétaire (UC-TDB-01 à 04), écran à part depuis la page
 * d'accueil minimale (specs § 15.1) : période, chiffres, résultats, barres, blocs d'état,
 * alertes ; le détail d'un chiffre (`?detail=…`) occupe tout l'écran. Chargé à la demande.
 */
export default function DashboardRoute({ shopId }: { shopId: string }) {
  return (
    <ReportingProvider>
      <DashboardScreen shopId={shopId} />
    </ReportingProvider>
  );
}
