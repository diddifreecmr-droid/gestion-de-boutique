import { useMemo } from "react";
import { CirclePlus, ReceiptText } from "lucide-react";
import { useNavigate } from "react-router";
import { createHttpCustomers } from "../../core/gateways/httpCustomers";
import { createHttpSales } from "../../core/gateways/httpSales";
import { shopPath } from "../../core/profile/shopProfile";
import { useServices } from "../../core/services/servicesContext";
import { formatTime } from "../../shared/format";
import { Badge, Button, EmptyState, KpiCard, ListCard, ListCardRow } from "../../shared/ui";
import { MY_SALES_KEY, NEW_SALE_KEY, SALES_KEY, saleLink, type SaleRole } from "../sales/salesNav";
import { useDashboardModule } from "./dashboardModule";
import { DASHBOARD_KEY } from "./dashboardNav";
import { FiguresPending } from "./FiguresOffline";
import { count } from "./homeText";
import { useFigures } from "./reportingContext";
import { Section } from "./Section";
import { loadTodaySales, RECENT_LIMIT, type RecentSale } from "./todaySales";

export const SALES_OFFLINE = "Connexion nécessaire pour afficher les ventes du jour.";

function useTodaySales(shopId: string) {
  const services = useServices();
  const gateways = useMemo(
    () => ({ sales: createHttpSales(services), customers: createHttpCustomers(services) }),
    [services],
  );
  return useFigures(`today-sales:${shopId}`, () => loadTodaySales(gateways, shopId));
}

function RecentRow({ sale, href }: { sale: RecentSale; href: string }) {
  const navigate = useNavigate();
  const badge = sale.cancelled ? (
    <Badge status="danger">Annulée</Badge>
  ) : sale.credit ? (
    <Badge status="credit">Crédit</Badge>
  ) : undefined;
  return (
    <ListCardRow
      title={sale.number}
      subtitle={`${sale.customer} · ${formatTime(sale.soldAt)}`}
      amount={sale.total}
      cancelled={sale.cancelled}
      {...(badge === undefined ? {} : { badge })}
      onOpen={() => void navigate(href)}
    />
  );
}

/** Ligne de vente : sa fiche dans la liste du rôle (`?id=`) ; le total : `totalTarget`. */
function TodayFigures({
  shopId,
  listPath,
  totalTarget,
}: {
  shopId: string;
  listPath: string;
  totalTarget: string;
}) {
  const navigate = useNavigate();
  const { loaded, retry } = useTodaySales(shopId);
  if (loaded.status !== "ready") {
    return (
      <FiguresPending
        status={loaded.status}
        onRetry={retry}
        label="Lecture des ventes du jour…"
        offlineMessage={SALES_OFFLINE}
      />
    );
  }
  const today = loaded.value;
  return (
    <>
      <KpiCard
        label="Ventes du jour"
        amount={today.total}
        detail={count(today.count, "vente", "ventes", "Aucune vente")}
        onOpen={() => void navigate(totalTarget)}
      />
      <Section title={`${String(RECENT_LIMIT)} dernières ventes`}>
        {today.recent.length === 0 ? (
          <EmptyState icon={ReceiptText} message="Aucune vente aujourd'hui" />
        ) : (
          <ListCard label="Dernières ventes">
            {today.recent.map((sale) => (
              <RecentRow key={sale.id} sale={sale} href={`${listPath}${saleLink(sale.id)}`} />
            ))}
          </ListCard>
        )}
      </Section>
    </>
  );
}

/** Propriétaire : « Ventes du jour » ouvre le tableau de bord complet si le module est actif. */
function OwnerFigures({ shopId }: { shopId: string }) {
  const { loaded } = useDashboardModule();
  const listPath = shopPath(shopId, SALES_KEY);
  const on = loaded.status === "ready" && loaded.value;
  return (
    <TodayFigures
      shopId={shopId}
      listPath={listPath}
      totalTarget={on ? shopPath(shopId, DASHBOARD_KEY) : listPath}
    />
  );
}

/** Vendeur : « Ventes du jour » ouvre « Mes ventes ». */
function SellerFigures({ shopId }: { shopId: string }) {
  const listPath = shopPath(shopId, MY_SALES_KEY);
  return <TodayFigures shopId={shopId} listPath={listPath} totalTarget={listPath} />;
}

/**
 * Page d'accueil minimale du propriétaire et du vendeur (specs § 15.1, décision client du
 * 12/11/2026) : grand bouton « Nouvelle vente », total des ventes du jour, 5 dernières ventes.
 * Vendeur : **ses** ventes seulement (filtrées par le serveur), sans coût ni marge.
 */
export function SalesHome({ shopId, role }: { shopId: string; role: SaleRole }) {
  const navigate = useNavigate();
  return (
    <>
      <Button
        size="lg"
        fullWidth
        icon={CirclePlus}
        onClick={() => void navigate(shopPath(shopId, NEW_SALE_KEY))}
      >
        Nouvelle vente
      </Button>
      {role === "owner" ? <OwnerFigures shopId={shopId} /> : <SellerFigures shopId={shopId} />}
    </>
  );
}
