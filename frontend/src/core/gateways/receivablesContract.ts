/**
 * Passerelle des écrans Créances et versements (specs § 4.6, § 6.3, T17) : l'écran dépend de
 * cette interface, jamais de `fetch`. Tous les types viennent du contrat **généré**.
 *
 * Droits (serveur) : propriétaire, tout ; vendeur, ses créances (vendeur responsable) et
 * les versements de ses clients (sinon 404) ; comptable et chauffeur, 403.
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type Receivable = Schemas["ReceivableResponse"];
export type ReceivableList = Schemas["ReceivableListResponse"];
export type ReceivableStatus = Schemas["ReceivableStatus"];
export type SeniorityBand = Schemas["SeniorityBand"];
export type Installment = Schemas["InstallmentResponse"];
export type InstallmentResult = Schemas["InstallmentResultResponse"];
export type InstallmentReceipt = Schemas["InstallmentReceiptResponse"];
export type InstallmentCreate = Schemas["InstallmentRequest"];
export type Reminder = Schemas["ReminderResponse"];
export type ReminderCreate = Schemas["ReminderRequest"];
export type ReminderPatch = Schemas["ReminderPatch"];
export type Guarantor = Schemas["GuarantorResponse"];
export type GuarantorCreate = Schemas["GuarantorRequest"];
export type LegacyReceivableCreate = Schemas["LegacyReceivableRequest"];
export type ReceivablePatch = Schemas["ReceivablePatch"];
export type Statement = Schemas["StatementResponse"];
export type StatementLine = Schemas["StatementLineResponse"];
export type CustomerSummary = Schemas["CustomerResponse"];
export type PaymentMode = Schemas["PaymentModeResponse"];
export type Member = Schemas["MemberResponse"];

/** Filtres de `GET /receivables` (absents = toutes, triées par reste décroissant). */
export interface ReceivableFilters {
  status?: ReceivableStatus;
  seller_id?: string;
  band?: SeniorityBand;
  /** Rappel dont la date est passée et qui n'est pas fait. */
  reminder_overdue?: boolean;
  /** Sans versement depuis plus de 30 jours. */
  quiet?: boolean;
}

export interface ReceivablesGateway {
  list(shopId: string, filters: ReceivableFilters): Promise<ReceivableList>;
  get(shopId: string, receivableId: string): Promise<Receivable>;
  /** Créance ancienne (UC-CRE-02, propriétaire) ; `id` client idempotent. */
  recordLegacy(shopId: string, body: LegacyReceivableCreate): Promise<Receivable>;
  /** `version` obligatoire ; `responsible_seller_id` : propriétaire seul. */
  change(shopId: string, receivableId: string, patch: ReceivablePatch): Promise<Receivable>;
  /** `capturedAt` : heure de l'appareil, envoyée en `X-Captured-At`. */
  pay(
    shopId: string,
    receivableId: string,
    body: InstallmentCreate,
    capturedAt: Date,
  ): Promise<InstallmentResult>;
  /** Propriétaire : motif obligatoire ; le reste est recalculé (UC-CRE-08). */
  cancelInstallment(
    shopId: string,
    installmentId: string,
    reason: string,
  ): Promise<InstallmentResult>;
  receipt(shopId: string, installmentId: string): Promise<InstallmentReceipt>;
  /** Propriétaire : motif obligatoire (UC-CRE-09). */
  writeOff(shopId: string, receivableId: string, reason: string): Promise<Receivable>;
  addReminder(shopId: string, receivableId: string, body: ReminderCreate): Promise<Receivable>;
  changeReminder(shopId: string, reminderId: string, patch: ReminderPatch): Promise<Receivable>;
  addGuarantor(shopId: string, receivableId: string, body: GuarantorCreate): Promise<Receivable>;
  statement(shopId: string, customerId: string): Promise<Statement>;
  /** `GET /customers?q=` : clients de la boutique (ceux du vendeur pour un vendeur). */
  searchCustomers(shopId: string, query: string): Promise<CustomerSummary[]>;
  paymentModes(shopId: string): Promise<PaymentMode[]>;
  /** Propriétaire seulement (`MEMBER_MANAGE`) : noms des vendeurs. */
  members(shopId: string): Promise<Member[]>;
}
