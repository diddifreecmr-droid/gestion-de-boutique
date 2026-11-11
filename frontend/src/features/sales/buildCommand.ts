/** Brouillon → corps exact de `POST /shops/{id}/sales` (specs § 6.4). */
import type {
  CustomerKind,
  RecordSaleCommand,
  SaleCustomerInput,
  SalePaymentInput,
  SoldDetailInput,
} from "../../core/gateways/salesContract";
import { BUSINESS_TIME_ZONE } from "../../shared/format";
import { CREDIT_CHOICE, type CustomerDraft, type SaleDraft, type UnitDetail } from "./draft";
import { normalizePhone } from "./phone";

/** Jour métier « AAAA-MM-JJ » à Douala (la date du jour est pré-remplie, CDC § 1.3). */
export function businessDay(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: BUSINESS_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

function orNull(text: string): string | null {
  const trimmed = text.trim();
  return trimmed === "" ? null : trimmed;
}

/** Seules les unités renseignées partent : une entrée = une moto (CDC § 17.3). */
function details(units: readonly UnitDetail[]): SoldDetailInput[] {
  return units
    .map((unit) => ({
      color: orNull(unit.color),
      chassis_number: orNull(unit.chassis)?.toUpperCase() ?? null,
      engine_number: orNull(unit.engine)?.toUpperCase() ?? null,
    }))
    .filter((detail) => Object.values(detail).some((value) => value !== null));
}

/** Type de client lu de l'API (`string`) : une valeur inconnue est une rupture de contrat. */
export function customerKind(kind: string): CustomerKind {
  if (kind === "individual" || kind === "company") return kind;
  throw new Error(`Type de client inconnu : « ${kind} »`);
}

function customerInput(customer: CustomerDraft): SaleCustomerInput | null {
  if (customer.mode === "none") return null;
  if (customer.mode === "existing") {
    const { id, name, phone, kind } = customer.customer;
    return { id, name, phone, kind: customerKind(kind) };
  }
  const phone = normalizePhone(customer.phone);
  if (phone === null) throw new Error("buildCommand : téléphone invalide (contrôle sauté ?)");
  return { id: null, name: customer.name.trim(), phone, kind: customer.kind };
}

function payments(draft: SaleDraft, total: number): SalePaymentInput[] {
  const reference = orNull(draft.reference);
  if (draft.payment === null) throw new Error("buildCommand : aucun mode de paiement choisi");
  if (draft.payment === CREDIT_CHOICE) {
    const deposit = draft.deposit ?? 0;
    if (deposit === 0) return [];
    if (draft.depositMode === null) throw new Error("buildCommand : mode de l'acompte absent");
    return [{ mode_id: draft.depositMode, amount: deposit, reference }];
  }
  if (draft.split === null) return [{ mode_id: draft.payment, amount: total, reference }];
  return Object.entries(draft.split)
    .filter((entry): entry is [string, number] => entry[1] !== null && entry[1] > 0)
    .map(([modeId, amount]) => ({ mode_id: modeId, amount, reference: null }));
}

export function buildCommand(
  draft: SaleDraft,
  locationId: string,
  total: number,
  now: Date = new Date(),
): RecordSaleCommand {
  const credit = draft.payment === CREDIT_CHOICE;
  return {
    id: draft.saleId,
    location_id: locationId,
    sold_on: businessDay(now),
    kind: credit ? "credit" : "cash",
    customer: customerInput(draft.customer),
    lines: draft.lines.map((line) => {
      if (line.unitPrice === null) throw new Error("buildCommand : prix vide (contrôle sauté ?)");
      return {
        article_id: line.article.id,
        sale_mode: line.article.sale_mode,
        quantity: String(line.quantity),
        unit_price: line.unitPrice,
        details: details(line.units),
      };
    }),
    payments: payments(draft, total),
    credit: credit
      ? { reminder_on: orNull(draft.reminderOn), terms: orNull(draft.terms), guarantor: null }
      : null,
    price_request_id: null,
    note: orNull(draft.note),
  };
}
