/**
 * Passerelle de la console plateforme (TR-23, UC-SOC-01, specs § 6.3) : boutiques, ouverture
 * d'une boutique et de son propriétaire, statut, droits d'offre, délégation. Types **générés**.
 *
 * Droits (serveur) : administrateur plateforme seul (403 pour un membre). Aucune donnée métier
 * d'une boutique ici. La délégation (24 h) est **accordée par le propriétaire** depuis sa
 * boutique : la console la montre, elle ne peut ni l'accorder ni la prolonger (CDC § 4.1).
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type ShopSummary = Schemas["ShopSummaryResponse"];
export type OpenShopInput = Schemas["OpenShopRequest"];
export type OpenedShop = Schemas["OpenedShopResponse"];
export type AdministerShop = Schemas["AdministerShopRequest"];
export type ShopAccess = Schemas["PlatformShopAccessResponse"];
export type EntitlementState = Schemas["EntitlementStateResponse"];
export type Entitlement = Schemas["Entitlement"];
export type ShopStatus = Schemas["ShopStatus"];

export interface PlatformGateway {
  list(): Promise<ShopSummary[]>;
  /** Le code provisoire du propriétaire n'est renvoyé qu'**une fois**, ici. */
  open(input: OpenShopInput): Promise<OpenedShop>;
  get(shopId: string): Promise<ShopSummary>;
  administer(shopId: string, change: AdministerShop): Promise<ShopSummary>;
  /** Droits d'offre en vigueur et fin de la délégation du propriétaire (ou `null`). */
  access(shopId: string): Promise<ShopAccess>;
}
