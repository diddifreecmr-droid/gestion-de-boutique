/** Créance ancienne (UC-CRE-02) : contrôles avant envoi et corps de `POST /receivables`. */
import type { LegacyReceivableCreate } from "../../core/gateways/receivablesContract";
import type { SaleCustomerInput } from "../../core/gateways/salesContract";
import { customerKind } from "../sales/buildCommand";
import type { CustomerDraft } from "../sales/draft";
import { normalizePhone } from "../sales/phone";

export interface LegacyDraft {
  customer: CustomerDraft;
  amount: number | null;
  openedOn: string;
  description: string;
  /** `null` = aucun vendeur responsable. */
  sellerId: string | null;
  terms: string;
}

export interface LegacyProblems {
  customer?: string;
  name?: string;
  phone?: string;
  amount?: string;
  date?: string;
  description?: string;
}

export const emptyLegacy = (): LegacyDraft => ({
  customer: { mode: "none" },
  amount: null,
  openedOn: "",
  description: "",
  sellerId: null,
  terms: "",
});

export function legacyProblems(draft: LegacyDraft, today: string): LegacyProblems {
  const problems: LegacyProblems = {};
  const { customer } = draft;
  if (customer.mode === "none") problems.customer = "Choisissez ou créez le client";
  if (customer.mode === "new") {
    if (customer.name.trim() === "") problems.name = "Le nom est vide";
    if (normalizePhone(customer.phone) === null) {
      problems.phone = "Le téléphone doit avoir 9 chiffres";
    }
  }
  if (draft.amount === null || draft.amount <= 0) problems.amount = "Le montant est vide";
  if (draft.openedOn === "") problems.date = "La date d'origine est vide";
  else if (draft.openedOn > today) problems.date = "Une date dans le futur est refusée";
  if (draft.description.trim() === "") problems.description = "La description est vide";
  return problems;
}

function customerInput(customer: CustomerDraft): SaleCustomerInput {
  if (customer.mode === "none")
    throw new Error("Créance ancienne sans client (contrôles contournés)");
  if (customer.mode === "existing") {
    const { id, name, phone, kind } = customer.customer;
    return { id, name, phone, kind: customerKind(kind) };
  }
  const phone = normalizePhone(customer.phone);
  if (phone === null) throw new Error("Téléphone invalide envoyé (contrôles contournés)");
  return { id: null, name: customer.name.trim(), phone, kind: customer.kind };
}

export function legacyBody(draft: LegacyDraft, id: string): LegacyReceivableCreate {
  if (draft.amount === null)
    throw new Error("Créance ancienne sans montant (contrôles contournés)");
  const terms = draft.terms.trim();
  return {
    id,
    customer: customerInput(draft.customer),
    amount: draft.amount,
    opened_on: draft.openedOn,
    description: draft.description.trim(),
    responsible_seller_id: draft.sellerId,
    terms: terms === "" ? null : terms,
  };
}
