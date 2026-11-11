/**
 * Passerelle des écrans Achats (specs § 4.6, § 6.3 « Achats ») : l'écran dépend de cette
 * interface, jamais de `fetch`. Tous les types viennent du contrat **généré** (schema.gen.ts).
 * Seuls le propriétaire et le comptable y accèdent (vendeur et chauffeur : 403, RG-D02).
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type Purchase = Schemas["PurchaseResponse"];
export type PurchasePage = Schemas["PurchasePageResponse"];
export type PurchaseTotals = Schemas["PurchaseTotalsResponse"];
export type PurchaseCreate = Schemas["PurchaseCreateRequest"];
export type PurchasePatch = Schemas["PurchasePatch"];
export type PurchaseLine = Schemas["LineResponse"];
export type PurchaseFee = Schemas["FeeResponse"];
export type SupplierPayment = Schemas["PaymentResponse"];
export type PaymentRequest = Schemas["PaymentRequest"];
export type LineRequest = Schemas["LineRequest"];
export type FeeRequest = Schemas["FeeRequest"];
export type FeeKind = Schemas["FeeKind"];
export type EntryUnit = Schemas["EntryUnit"];
export type Supplier = Schemas["SupplierResponse"];
export type SupplierRequest = Schemas["SupplierRequest"];
export type SupplierPatch = Schemas["SupplierPatch"];
export type SupplierSheet = Schemas["SupplierSheetResponse"];
export type PurchaseLocation = Schemas["LocationResponse"];
export type PurchasePaymentMode = Schemas["PaymentModeResponse"];

/** Filtres de `GET /purchases` (absents = mois en cours, tous fournisseurs, articles, lieux). */
export interface PurchaseFilters {
  from?: string;
  to?: string;
  supplier_id?: string;
  article_id?: string;
  location_id?: string;
}

/** Période de la fiche fournisseur (absente = mois en cours). */
export interface SupplierPeriod {
  from?: string;
  to?: string;
}

export interface PurchasingGateway {
  list(shopId: string, filters: PurchaseFilters, cursor?: string): Promise<PurchasePage>;
  get(shopId: string, purchaseId: string): Promise<Purchase>;
  /** `422 PRICE_GAP_CONFIRMATION_REQUIRED` tant que `confirm_price_gap` n'est pas vrai. */
  record(shopId: string, body: PurchaseCreate): Promise<Purchase>;
  correct(shopId: string, purchaseId: string, patch: PurchasePatch): Promise<Purchase>;
  /** Propriétaire seulement (`PURCHASE_CANCEL`). */
  cancel(shopId: string, purchaseId: string, reason: string): Promise<Purchase>;
  pay(shopId: string, purchaseId: string, body: PaymentRequest): Promise<Purchase>;
  suppliers(shopId: string): Promise<Supplier[]>;
  createSupplier(shopId: string, body: SupplierRequest): Promise<Supplier>;
  updateSupplier(shopId: string, supplierId: string, patch: SupplierPatch): Promise<Supplier>;
  supplierSheet(shopId: string, supplierId: string, period: SupplierPeriod): Promise<SupplierSheet>;
  locations(shopId: string): Promise<PurchaseLocation[]>;
  paymentModes(shopId: string): Promise<PurchasePaymentMode[]>;
  /** Lieu de réception par défaut (réglages) — propriétaire seulement (`SETTINGS_MANAGE`). */
  receptionLocation(shopId: string): Promise<string | null>;
}
