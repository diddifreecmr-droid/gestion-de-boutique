/**
 * Corps des requêtes d'achat à partir du brouillon, une fois les contrôles passés : un champ
 * manquant ici est un contrôle oublié (fail-fast), jamais une valeur inventée.
 */
import type {
  FeeRequest,
  LineRequest,
  Purchase,
  PurchaseCreate,
  PurchasePatch,
} from "../../core/gateways/purchasingContract";
import { DEFAULT_LOCATION, type FeeDraft, type LineDraft, type PurchaseDraft } from "./draft";
import { parseEntryQuantity } from "./units";

function required<T>(value: T | null, name: string): T {
  if (value === null) throw new Error(`Brouillon d'achat incomplet : ${name} (contrôle oublié)`);
  return value;
}

const optional = (text: string) => (text.trim() === "" ? null : text.trim());

export function lineRequest(line: LineDraft): LineRequest {
  const unit = required(line.unit, "unité");
  const quantity = parseEntryQuantity(line.quantity, unit);
  if (!quantity.ok) throw new Error(`Quantité invalide envoyée : ${quantity.error}`);
  return {
    article_id: required(line.article, "article").id,
    quantity: quantity.value,
    unit,
    unit_price: required(line.unitPrice, "prix unitaire"),
  };
}

export function feeRequest(fee: FeeDraft): FeeRequest {
  return {
    kind: fee.kind,
    amount: required(fee.amount, "montant des frais"),
    label: optional(fee.label),
  };
}

/** `POST /purchases` ; date du jour → omise (journée métier du serveur), lieu par défaut → omis. */
export function createBody(
  draft: PurchaseDraft,
  id: string,
  today: string,
  confirmPriceGap: boolean,
): PurchaseCreate {
  return {
    id,
    lines: draft.lines.map(lineRequest),
    fees: draft.fees.map(feeRequest),
    purchase_date: draft.date === today ? null : draft.date,
    location_id: draft.locationId === DEFAULT_LOCATION ? null : draft.locationId,
    supplier_id: draft.supplier?.id ?? null,
    invoice_ref: optional(draft.invoiceRef),
    note: optional(draft.note),
    confirm_price_gap: confirmPriceGap,
  };
}

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

/** `PATCH /purchases/{id}` : `version`, `reason` et les seuls champs changés. */
export function patchBody(
  draft: PurchaseDraft,
  purchase: Purchase,
  reason: string,
  confirmPriceGap: boolean,
): PurchasePatch {
  const patch: PurchasePatch = {
    version: purchase.version,
    reason,
    confirm_price_gap: confirmPriceGap,
  };
  const lines = draft.lines.map(lineRequest);
  const before = purchase.lines.map((line) => ({
    article_id: line.article_id,
    quantity: line.quantity,
    unit: line.unit,
    unit_price: line.unit_price,
  }));
  if (!same(lines, before)) patch.lines = lines;
  const fees = draft.fees.map(feeRequest);
  if (
    !same(
      fees,
      purchase.fees.map(({ kind, amount, label }) => ({ kind, amount, label })),
    )
  ) {
    patch.fees = fees;
  }
  if (draft.date !== purchase.purchase_date) patch.purchase_date = draft.date;
  if (draft.locationId !== purchase.location_id) patch.location_id = draft.locationId;
  const supplierId = draft.supplier?.id ?? null;
  if (supplierId !== purchase.supplier_id) patch.supplier_id = supplierId;
  const invoice = optional(draft.invoiceRef);
  if (invoice !== purchase.invoice_ref) patch.invoice_ref = invoice;
  const note = optional(draft.note);
  if (note !== purchase.note) patch.note = note;
  return patch;
}
