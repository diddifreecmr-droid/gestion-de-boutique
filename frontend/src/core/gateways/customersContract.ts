/**
 * Passerelle des Clients (UC-VEN-11, specs § 6.3) : recherche, fiche (total acheté, total dû,
 * ventes), création et modification. Types issus du contrat **généré**.
 *
 * Droits (serveur) : propriétaire (tous les clients) et vendeur (les siens) ; comptable et
 * chauffeur → 403 (RG-D03). Téléphone déjà pris → 409 ; modification concurrente → 409
 * (`version`). Aucun coût d'achat dans la fiche : seulement les montants de vente.
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type Customer = Schemas["CustomerResponse"];
export type CustomerSheet = Schemas["CustomerSheetResponse"];
export type CustomerKind = Schemas["CustomerKind"];
export type CustomerInput = Schemas["CustomerCreateRequest"];
export type CustomerChanges = Schemas["CustomerPatch"];
export type CustomerSale = Schemas["SaleResponse"];

export interface CustomersGateway {
  /** `GET /customers?q=` ; `q` vide : les clients récents de la boutique. */
  search(shopId: string, query: string): Promise<Customer[]>;
  sheet(shopId: string, customerId: string): Promise<CustomerSheet>;
  create(shopId: string, input: CustomerInput): Promise<Customer>;
  update(shopId: string, customerId: string, changes: CustomerChanges): Promise<Customer>;
}
