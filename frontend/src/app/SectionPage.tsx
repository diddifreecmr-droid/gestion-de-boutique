import { lazy, Suspense } from "react";
import { useParams } from "react-router";
import { findSection } from "../core/profile/shopProfile";
import { MORE_KEY } from "../core/profile/types";
import { NEW_SALE_KEY, SALES_KEY, SalesHome } from "../features/sales/SalesHome";
import { SALE_ROLES } from "../features/sales/saleRoles";
import { AccountPage } from "../features/settings/AccountPage";
import { EXPENSES_KEY } from "../features/expenses/expenseNav";
import { CATALOG_ROLES, STOCK_KEY } from "../features/catalog/catalogRights";
import { ComingSoon } from "./ComingSoon";
import { NotFoundPage } from "./NotFoundPage";
import { MorePage } from "./MorePage";
import { ACCOUNT_KEY } from "./RoleHome";
import { useActiveShop } from "./shopContext";
import { Skeleton } from "../shared/ui";

/** Écran chargé à la demande (specs § 4.6) : il ne pèse pas sur le premier affichage. */
const NewSaleRoute = lazy(() => import("../features/sales/NewSaleRoute"));
const ExpensesRoute = lazy(() => import("../features/expenses/ExpensesRoute"));
const CatalogRoute = lazy(() => import("../features/catalog/CatalogRoute"));

/** Écrans communs à tous les rôles, hors barre du bas. */
const SETTINGS_KEY = "reglages";
const ALERTS_KEY = "alertes";

/**
 * `/s/{shopId}/{section}` : une section absente du menu du rôle n'existe pas pour lui
 * (CDC § 1.3 : ce qu'il n'a pas le droit de faire n'apparaît pas du tout).
 */
export function SectionPage() {
  const { section = "" } = useParams();
  const { shopId, role, profile } = useActiveShop();
  if (section === ACCOUNT_KEY) return <AccountPage title="Mon compte" />;
  if (section === ALERTS_KEY) return <ComingSoon title="Alertes" />;
  // « Nouvelle vente » : entrée du menu vendeur ; le propriétaire y vient depuis « Ventes ».
  if (section === NEW_SALE_KEY && SALE_ROLES.includes(role)) {
    return (
      <Suspense fallback={<Skeleton lines={4} label="Ouverture de la vente…" />}>
        <NewSaleRoute shopId={shopId} role={role} />
      </Suspense>
    );
  }
  const entry = findSection(profile, role, section);
  if (entry === null) return <NotFoundPage />;
  if (entry.key === MORE_KEY) return <MorePage />;
  if (entry.key === SETTINGS_KEY) return <AccountPage title={entry.label} />;
  if (entry.key === SALES_KEY) return <SalesHome shopId={shopId} title={entry.label} />;
  if (entry.key === EXPENSES_KEY) {
    return (
      <Suspense fallback={<Skeleton lines={4} label="Ouverture des dépenses…" />}>
        <ExpensesRoute shopId={shopId} role={role} />
      </Suspense>
    );
  }
  // « Stock » du propriétaire et du comptable : le catalogue (le vendeur attend le module Stock).
  if (entry.key === STOCK_KEY && CATALOG_ROLES.includes(role)) {
    return (
      <Suspense fallback={<Skeleton lines={4} label="Ouverture des articles…" />}>
        <CatalogRoute shopId={shopId} role={role} />
      </Suspense>
    );
  }
  return <ComingSoon title={entry.label} />;
}
