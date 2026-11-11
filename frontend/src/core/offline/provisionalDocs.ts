/**
 * Documents **provisoires** rendus à l'écran pour une saisie mise en file (UC-VEN-10, RG-T06) :
 * même forme que la réponse du serveur, numéro `V-HL-…` / `D-HL-…`, avertissement
 * `OFFLINE_QUEUED` (« la saisie partira au retour du réseau »). Rien n'y est inventé : noms et
 * unités viennent de l'instantané hors ligne (RG-T25) ; un article absent est une erreur.
 * Les identifiants que seul le serveur connaît (auteur, lieu habituel) restent vides.
 */
import type { Expense, ExpenseCreate } from "../gateways/expensesContract";
import type { RecordSaleCommand, SaleResult } from "../gateways/salesContract";
import type { OfflineSnapshot } from "./contract";

export const OFFLINE_QUEUED = {
  code: "OFFLINE_QUEUED",
  message: "Hors connexion : la saisie partira au retour du réseau (numéro provisoire).",
  details: {},
};

export interface ProvisionalDoc {
  id: string;
  number: string;
  capturedAt: Date;
  deviceId: string;
  /** Jour métier de la saisie (« AAAA-MM-JJ », Douala). */
  today: string;
}

function article(snapshot: OfflineSnapshot, id: string) {
  const found = snapshot.articles.find((a) => a.id === id);
  if (found === undefined) throw new Error(`Article ${id} absent de l'instantané hors ligne`);
  return found;
}

function saleLines(command: RecordSaleCommand, snapshot: OfflineSnapshot) {
  return command.lines.map((line) => {
    const known = article(snapshot, line.article_id);
    return {
      article_id: line.article_id,
      article_name: known.display_name,
      sale_mode: line.sale_mode ?? "unit",
      quantity: line.quantity,
      stock_quantity: line.quantity,
      stock_unit: known.stock_unit,
      base_price: known.base_price,
      unit_price: line.unit_price,
      line_total: Math.round(Number(line.quantity) * line.unit_price),
      details: (line.details ?? []).map((d) => ({
        color: d.color ?? null,
        chassis_number: d.chassis_number ?? null,
        engine_number: d.engine_number ?? null,
        size: d.size ?? null,
      })),
    };
  });
}

export function provisionalSale(
  command: RecordSaleCommand,
  snapshot: OfflineSnapshot,
  doc: ProvisionalDoc,
): SaleResult {
  const lines = saleLines(command, snapshot);
  const payments = (command.payments ?? []).map((p, index) => ({
    id: p.id ?? `${doc.id}-${String(index)}`,
    mode_id: p.mode_id,
    amount: p.amount,
    reference: p.reference ?? null,
    nature: command.kind === "credit" ? "deposit" : "payment",
  }));
  const total = lines.reduce((sum, line) => sum + line.line_total, 0);
  const paid = payments.reduce((sum, p) => sum + p.amount, 0);
  const at = doc.capturedAt.toISOString();
  const credit = command.credit ?? null;
  return {
    id: doc.id,
    number: doc.number,
    provisional_number: doc.number,
    status: "valid",
    kind: command.kind,
    sold_on: command.sold_on ?? doc.today,
    sold_at: at,
    location_id: command.location_id ?? "",
    seller_id: command.seller_id ?? "",
    customer_id: command.customer?.id ?? null,
    total,
    paid,
    remaining: total - paid,
    receivable: null,
    lines,
    payments,
    credit:
      credit === null
        ? null
        : { reminder_on: credit.reminder_on ?? null, terms: credit.terms ?? null },
    note: command.note ?? null,
    stock_to_verify: false,
    cancellation: null,
    created_by: "",
    device_id: doc.deviceId,
    captured_at: at,
    received_at: at,
    editable: false,
    version: 0,
    warnings: [OFFLINE_QUEUED],
    error_reports: [],
  };
}

export function provisionalExpense(body: ExpenseCreate, doc: ProvisionalDoc): Expense {
  const at = doc.capturedAt.toISOString();
  return {
    id: doc.id,
    number: doc.number,
    spent_on: body.spent_on ?? doc.today,
    amount: body.amount,
    category_id: body.category_id,
    payment_mode_id: body.payment_mode_id ?? "",
    tags: [],
    description: body.description ?? null,
    location_id: body.location_id ?? null,
    beneficiary: body.beneficiary ?? null,
    attachment_id: body.attachment_id ?? null,
    status: "valid",
    created_by: "",
    device_id: doc.deviceId,
    captured_at: at,
    received_at: at,
    cancellation: null,
    editable: false,
    correction_deadline: at,
    version: 0,
  };
}
