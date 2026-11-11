/**
 * Passerelle du Tableau de bord et des accueils par rôle (specs § 4.6, § 6.3, T19) : l'écran
 * dépend de cette interface, jamais de `fetch`. Tous les types viennent du contrat **généré**.
 *
 * Droits (serveur) : `dashboard` et `detail` pour le propriétaire seul (403 sinon) ; `home`
 * pour tous les membres, avec **un seul** bloc rempli, celui du rôle (le vendeur n'y a ni
 * marge ni coût, le comptable ni vente — RG-D02, RG-D03). Réponses en `no-store` (RG-T25).
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type Dashboard = Schemas["DashboardResponse"];
export type DashboardDetail = Schemas["DashboardDetailResponse"];
export type DetailLine = Schemas["DetailLineOut"];
export type DetailMetric = Schemas["DetailMetric"];
export type PeriodKind = Schemas["PeriodKind"];
export type PeriodOut = Schemas["PeriodOut"];
export type Compared = Schemas["Compared"];
export type NotAvailable = Schemas["NotAvailable"];
export type Series = Schemas["Series"];
export type Valuation = Schemas["Valuation"];
export type Home = Schemas["HomeResponse"];
export type SellerHome = Schemas["SellerHomeOut"];
export type AccountantHome = Schemas["AccountantHomeOut"];
export type DriverHome = Schemas["DriverHomeOut"];

/** Période demandée : `from` / `to` (AAAA-MM-JJ) seulement pour la période libre. */
export type PeriodQuery =
  { period: Exclude<PeriodKind, "custom"> } | { period: "custom"; from: string; to: string };

export interface ReportingGateway {
  /** UC-TDB-01 / 02 : indicateurs de la période, comparés à la période précédente. */
  dashboard(shopId: string, period: PeriodQuery): Promise<Dashboard>;
  /** UC-TDB-04 : la liste qui explique un chiffre ; son total est le chiffre affiché. */
  detail(shopId: string, metric: DetailMetric, period: PeriodQuery): Promise<DashboardDetail>;
  /** UC-TDB-05 : accueil du rôle de l'utilisateur dans la boutique. */
  home(shopId: string): Promise<Home>;
}
