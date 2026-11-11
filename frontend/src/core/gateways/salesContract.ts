/**
 * Contrat de la vente (specs § 6.4), recopié champ pour champ : `snake_case`, montants en
 * entiers FCFA, quantités en chaînes décimales (« "1" », « "2.5" »).
 *
 * PROVISOIRE : ces types seront remplacés par des alias de `schema.gen.ts` quand
 * `POST /shops/{id}/sales` existera (T16 / T21) ; les noms et les formes ne doivent pas bouger.
 * Les ajouts qui ne figurent pas dans specs § 6.4 sont marqués « HYPOTHÈSE ».
 */

/** Chaîne décimale positive de l'API (« "1" », « "2.500" »). */
export type DecimalString = string;

export type SaleKind = "cash" | "credit";
export type CustomerKind = "individual" | "company";
/** Mode de vente d'une ligne ; le profil « motos » ne vend qu'à l'unité. */
export type SaleMode = "unit";

/** Client de la vente : existant (`id`) ou créé à la volée (`id: null`, UC-VEN-02, H20). */
export interface SaleCustomerInput {
  id: string | null;
  name: string;
  phone: string;
  kind: CustomerKind;
}

/** Détail d'une unité vendue (CDC § 17.3 : une entrée par moto, champs facultatifs). */
export interface SoldDetailInput {
  color: string | null;
  chassis_number: string | null;
  /** Présent dans le modèle (specs § 5.4 SOLD_DETAIL), absent de l'exemple § 6.4. */
  engine_number: string | null;
}

export interface SaleLineInput {
  article_id: string;
  sale_mode: SaleMode;
  quantity: DecimalString;
  unit_price: number;
  details: SoldDetailInput[];
}

export interface SalePaymentInput {
  mode_id: string;
  amount: number;
  reference: string | null;
}

export interface SaleCreditInput {
  /** Date de rappel « AAAA-MM-JJ » (facultative). */
  reminder_on: string | null;
  /** Conditions convenues (« 100 000 par mois »). */
  terms: string | null;
  /** Garant : hors périmètre de cet écran (UC-VEN-02 étape 3, T21). */
  guarantor: null;
}

/** Corps de `POST /api/v1/shops/{shop_id}/sales`. `id` (UUIDv7) rend l'envoi idempotent. */
export interface RecordSaleCommand {
  id: string;
  location_id: string;
  sold_on: string;
  kind: SaleKind;
  customer: SaleCustomerInput | null;
  lines: SaleLineInput[];
  payments: SalePaymentInput[];
  credit: SaleCreditInput | null;
  price_request_id: string | null;
  note: string | null;
}

export interface SaleLineResult {
  article_name: string;
  quantity: DecimalString;
  unit_price: number;
  line_total: number;
}

/** HYPOTHÈSE : forme d'un avertissement (specs § 6.4 ne montre que `[]`). */
export interface SaleWarning {
  code: string;
  message: string;
}

/**
 * Réponse `201`, présentateur **vendeur** (TR-05) : aucun coût, CMP ni marge. C'est le seul
 * type que lit l'écran ; la réponse propriétaire en est un sur-ensemble (ci-dessous).
 */
export interface SaleResult {
  id: string;
  number: string;
  status: "valid";
  kind: SaleKind;
  total: number;
  paid: number;
  remaining: number;
  receivable: { id: string; remaining: number } | null;
  lines: SaleLineResult[];
  warnings: SaleWarning[];
}

/** Présentateur propriétaire : coûts figés et marges par ligne (jamais lus par l'écran). */
export interface OwnerSaleLineResult extends SaleLineResult {
  frozen_last_cost: number;
  frozen_wac: number;
  margin: number;
  margin_wac: number;
}

/** HYPOTHÈSE : corps de `POST /price-requests` (UC-VEN-03) — à confirmer en T16. */
export interface PriceRequestCommand {
  id: string;
  location_id: string;
  article_id: string;
  requested_price: number;
}

export interface PriceRequestResult {
  id: string;
  status: "pending";
  /** La demande expire au bout de 30 minutes (UC-VEN-03). */
  expires_at: string;
}

export interface CustomerSummary {
  id: string;
  name: string;
  phone: string;
  kind: CustomerKind;
}

/**
 * Passerelle des ventes. Erreurs : `ApiError` (codes de specs § 6.2) ou `NetworkError`
 * (« Connexion nécessaire » ; aucune mise en file, `offline_capture` désactivé, TR-26).
 */
export interface SalesGateway {
  recordSale(shopId: string, command: RecordSaleCommand): Promise<SaleResult>;
  requestPriceApproval(shopId: string, command: PriceRequestCommand): Promise<PriceRequestResult>;
  /** `GET /customers?query=` : clients de la boutique (ceux du vendeur pour un vendeur). */
  searchCustomers(shopId: string, query: string): Promise<{ items: CustomerSummary[] }>;
}
