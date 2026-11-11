/**
 * Contrat des ventes (specs § 6.4, T16a) : alias **générés** de `schema.gen.ts`, jamais
 * réécrits. `snake_case`, montants en entiers FCFA, quantités en chaînes décimales.
 *
 * TR-05 : pour un vendeur, les clés `frozen_last_cost`, `frozen_wac`, `margin`, `margin_wac`
 * d'une ligne sont **absentes** du JSON ; pour le propriétaire, `null` = non calculable. Ce
 * que voit chaque rôle passe par `features/sales/saleView.ts`.
 */
import type { components } from "../api/schema.gen";
import type { SaleReturn, SaleReturnCommand, SaleReturns } from "./returnsContract";

type Schemas = components["schemas"];

/** Chaîne décimale positive de l'API (« "1" », « "2.500" »). */
export type DecimalString = string;

export type SaleKind = Schemas["SaleKind"];
export type CustomerKind = Schemas["CustomerKind"];
/** Mode de vente d'une ligne ; l'écran « Nouvelle vente » ne vend encore qu'à l'unité. */
export type SaleMode = Schemas["SaleMode"];

/** Corps de `POST /shops/{shop_id}/sales`. `id` (UUIDv7) rend l'envoi idempotent. */
export type RecordSaleCommand = Schemas["SaleCreateRequest"];
export type SaleCustomerInput = Schemas["SaleCustomerRequest"];
export type SaleLineInput = Schemas["SaleLineRequest"];
export type SalePaymentInput = Schemas["SalePaymentRequest"];
export type SoldDetailInput = Schemas["DetailRequest"];
export type SaleCreditInput = Schemas["CreditRequest"];

export type SaleResult = Schemas["SaleResponse"];
export type SaleLineResult = Schemas["SaleLineResponse"];
export type SalePaymentResult = Schemas["SalePaymentResponse"];
export type SoldDetail = Schemas["DetailResponse"];
/** Avertissement accepté (propriétaire) : `{code, message, details}`. */
export type SaleWarning = Schemas["WarningResponse"];
export type SalePage = Schemas["SalePageResponse"];
export type ErrorReport = Schemas["ErrorReportResponse"];
export type CustomerSummary = Schemas["CustomerResponse"];
export type SaleMember = Schemas["MemberResponse"];
/** DTO du reçu (UC-VEN-04) : aucun coût ni marge, quel que soit le rôle. */
export type Receipt = Schemas["SaleReceiptResponse"];
export type ReceiptLine = Schemas["ReceiptLineResponse"];

/** Critères de `GET /sales` (du jour par défaut ; `q` = numéro ou châssis, toutes dates). */
export interface SaleFilters {
  from?: string;
  to?: string;
  seller_id?: string;
  payment_mode_id?: string;
  kind?: SaleKind;
  q?: string;
}

/**
 * Demande d'accord pour un prix sous le minimum (UC-VEN-03, T16b). `status` est le statut
 * **effectif** à l'horloge du serveur : `pending`, `accepted`, `refused` ou `expired`. Le lieu
 * est celui du vendeur (le serveur le pose) ; `expires_at` : 30 min après la demande, puis
 * 30 min après l'accord.
 */
export type PriceRequest = Schemas["PriceRequestResponse"];
export type PriceRequestCommand = Schemas["PriceRequestCreate"];
export type PriceDecision = Schemas["PriceDecisionRequest"]["decision"];
export type PriceRequestStatus = "pending" | "accepted" | "refused" | "expired";

/** Statut lu de l'API (`string`) : une valeur inconnue est une rupture de contrat. */
export function priceRequestStatus(request: PriceRequest): PriceRequestStatus {
  const { status } = request;
  if (status === "pending" || status === "accepted" || status === "refused") return status;
  if (status === "expired") return status;
  throw new Error(`Statut de demande de prix inconnu : « ${status} »`);
}

/**
 * Passerelle des ventes. Erreurs : `ApiError` (codes de specs § 6.2) ou `NetworkError`
 * (« Connexion nécessaire » ; aucune mise en file, `offline_capture` désactivé, TR-26).
 */
export interface SalesGateway {
  /** `capturedAt` : heure de l'appareil, envoyée en `X-Captured-At` (ISO avec fuseau). */
  recordSale(shopId: string, command: RecordSaleCommand, capturedAt: Date): Promise<SaleResult>;
  /** Vendeur : `POST /price-requests` (`id` client idempotent). */
  requestPriceApproval(shopId: string, command: PriceRequestCommand): Promise<PriceRequest>;
  /** Vendeur : ses demandes ; propriétaire : celles en attente. */
  listPriceRequests(shopId: string): Promise<PriceRequest[]>;
  getPriceRequest(shopId: string, requestId: string): Promise<PriceRequest>;
  /** Propriétaire seulement ; `version` lue avec la demande. */
  decidePriceRequest(
    shopId: string,
    requestId: string,
    decision: PriceDecision,
    version: number,
  ): Promise<PriceRequest>;
  /** Propriétaire seulement (UC-VEN-09) : retour simple ou échange. */
  recordReturn(shopId: string, saleId: string, command: SaleReturnCommand): Promise<SaleReturn>;
  /** Retours de la vente et quantités encore rendables par ligne. */
  listReturns(shopId: string, saleId: string): Promise<SaleReturns>;
  /** `GET /customers?q=` : clients de la boutique (ceux du vendeur pour un vendeur). */
  searchCustomers(shopId: string, query: string): Promise<{ items: CustomerSummary[] }>;
  listSales(shopId: string, filters: SaleFilters, cursor: string | null): Promise<SalePage>;
  getSale(shopId: string, saleId: string): Promise<SaleResult>;
  /** Propriétaire seulement. */
  cancelSale(shopId: string, saleId: string, reason: string): Promise<SaleResult>;
  /** Vendeur, sur ses ventes ; `id` client idempotent. */
  reportError(
    shopId: string,
    saleId: string,
    body: { id: string; description: string },
  ): Promise<ErrorReport>;
  /** Chaque appel compte une impression : « Duplicata » dès la 2ᵉ. N'appeler qu'en imprimant. */
  receipt(shopId: string, saleId: string): Promise<Receipt>;
  /** Propriétaire seulement (`MEMBER_MANAGE`) : noms des vendeurs (filtre, fiche). */
  members(shopId: string): Promise<SaleMember[]>;
}
