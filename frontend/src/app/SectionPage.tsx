import { lazy, Suspense } from "react";
import { useParams } from "react-router";
import { findSection } from "../core/profile/shopProfile";
import { MORE_KEY } from "../core/profile/types";
import { MY_SALES_KEY, NEW_SALE_KEY, SALES_KEY } from "../features/sales/salesNav";
import { SALE_ROLES } from "../features/sales/saleRoles";
import { AccountPage } from "../features/settings/AccountPage";
import { EXPENSES_KEY } from "../features/expenses/expenseNav";
import { STOCK_KEY } from "../features/catalog/catalogRights";
import { STOCK_ROLES } from "../features/stock/stockRoles";
import { PURCHASE_ROLES, PURCHASES_KEY } from "../features/purchasing/purchasingNav";
import { RECEIVABLE_ROLES, RECEIVABLES_KEY } from "../features/receivables/receivablesNav";
import { ComingSoon } from "./ComingSoon";
import { NotFoundPage } from "./NotFoundPage";
import { MorePage } from "./MorePage";
import { ACCOUNT_KEY } from "./RoleHome";
import { useActiveShop } from "./shopContext";
import { Skeleton } from "../shared/ui";

/** Écran chargé à la demande (specs § 4.6) : il ne pèse pas sur le premier affichage. */
const NewSaleRoute = lazy(() => import("../features/sales/NewSaleRoute"));
const SalesRoute = lazy(() => import("../features/sales/SalesRoute"));
const ExpensesRoute = lazy(() => import("../features/expenses/ExpensesRoute"));
const StockRoute = lazy(() => import("../features/stock/StockRoute"));
const PurchasingRoute = lazy(() => import("../features/purchasing/PurchasingRoute"));
const ReceivablesRoute = lazy(() => import("../features/receivables/ReceivablesRoute"));

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
  // « Ventes » du propriétaire, « Mes ventes » du vendeur (UC-VEN-05).
  if ((entry.key === SALES_KEY || entry.key === MY_SALES_KEY) && SALE_ROLES.includes(role)) {
    return (
      <Suspense fallback={<Skeleton lines={4} label="Ouverture des ventes…" />}>
        <SalesRoute shopId={shopId} role={role} title={entry.label} />
      </Suspense>
    );
  }
  if (entry.key === EXPENSES_KEY) {
    return (
      <Suspense fallback={<Skeleton lines={4} label="Ouverture des dépenses…" />}>
        <ExpensesRoute shopId={shopId} role={role} />
      </Suspense>
    );
  }
  // « Achats » : entrée du comptable, « Plus → Achats » du propriétaire (CDC § 17.4).
  if (entry.key === PURCHASES_KEY && PURCHASE_ROLES.includes(role)) {
    return (
      <Suspense fallback={<Skeleton lines={4} label="Ouverture des achats…" />}>
        <PurchasingRoute shopId={shopId} role={role} />
      </Suspense>
    );
  }
  // « Créances » : entrée du vendeur, « Plus → Créances » du propriétaire (CDC § 17.4).
  if (entry.key === RECEIVABLES_KEY && RECEIVABLE_ROLES.includes(role)) {
    return (
      <Suspense fallback={<Skeleton lines={4} label="Ouverture des créances…" />}>
        <ReceivablesRoute shopId={shopId} role={role} />
      </Suspense>
    );
  }
  // « Stock » : matrice pour les trois rôles ; onglet « Articles » (catalogue), historique,
  // ajustement, inventaire et valeur pour le propriétaire et le comptable.
  if (entry.key === STOCK_KEY && STOCK_ROLES.includes(role)) {
    return (
      <Suspense fallback={<Skeleton lines={4} label="Ouverture du stock…" />}>
        <StockRoute shopId={shopId} role={role} />
      </Suspense>
    );
  }
  return <ComingSoon title={entry.label} />;
}
