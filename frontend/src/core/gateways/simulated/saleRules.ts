/**
 * Règles que le serveur simulé fait respecter (specs § 6.2) : chaque refus est une
 * `ApiError` au code et aux `details` du contrat, jamais un succès partiel.
 */
import { ApiError } from "../../api/errors";
import type { RecordSaleCommand, SaleWarning } from "../salesContract";
import { LOCATIONS } from "./seed";
import { requireArticle, type World } from "./world";

function invalid(message: string, field: string): never {
  throw new ApiError(400, "VALIDATION_ERROR", message, { fields: [field] });
}

function quantityOf(text: string): number {
  if (!/^\d+$/.test(text) || Number(text) < 1) invalid(`Quantité invalide « ${text} »`, "quantity");
  return Number(text);
}

export function saleTotal(command: RecordSaleCommand): number {
  return command.lines.reduce((sum, line) => sum + quantityOf(line.quantity) * line.unit_price, 0);
}

/** Paiements du corps (facultatifs dans le contrat : absents = aucun). */
export function paymentsOf(command: RecordSaleCommand) {
  return command.payments ?? [];
}

/** Lieu de la vente : le simulateur exige qu'il soit donné (le vrai serveur le déduit). */
export function locationOf(command: RecordSaleCommand): string {
  const location = command.location_id;
  if (location === undefined || location === null) invalid("Lieu de vente absent", "location_id");
  return location;
}

export function checkShape(command: RecordSaleCommand): void {
  if (command.lines.length === 0) invalid("La vente n'a aucune ligne", "lines");
  locationOf(command);
  command.lines.forEach((line) => {
    if (!Number.isSafeInteger(line.unit_price) || line.unit_price < 1) {
      invalid("Le prix doit être un entier positif", "unit_price");
    }
  });
  paymentsOf(command).forEach((payment) => {
    if (!Number.isSafeInteger(payment.amount) || payment.amount < 1) {
      invalid("Un paiement doit être un montant positif", "payments");
    }
  });
  if (command.kind === "credit") {
    const customer = command.customer;
    const blank = (text: string | null | undefined) => (text ?? "").trim() === "";
    if (
      customer === null ||
      customer === undefined ||
      blank(customer.name) ||
      blank(customer.phone)
    ) {
      invalid("Client obligatoire (nom et téléphone) pour une vente à crédit", "customer");
    }
  }
}

export function checkStock(world: World, command: RecordSaleCommand): void {
  command.lines.forEach((line) => {
    const article = requireArticle(world, line.article_id);
    const here = locationOf(command);
    const available = article.stock[here] ?? 0;
    if (quantityOf(line.quantity) <= available) return;
    const others = LOCATIONS.filter((location) => location.id !== here)
      .map((location) => ({ location, quantity: article.stock[location.id] ?? 0 }))
      .filter((entry) => entry.quantity > 0)
      .map((entry) => ({
        location_id: entry.location.id,
        location_name: entry.location.name,
        available: String(entry.quantity),
      }));
    throw new ApiError(422, "STOCK_INSUFFICIENT", `Stock insuffisant : ${article.name}`, {
      article_id: article.id,
      available: String(available),
      other_locations: others,
    });
  });
}

export function checkPayments(command: RecordSaleCommand, total: number): void {
  const paid = paymentsOf(command).reduce((sum, payment) => sum + payment.amount, 0);
  if (paid > total) {
    throw new ApiError(422, "OVERPAYMENT", "Le total payé dépasse le montant de la vente", {
      total,
      paid,
    });
  }
  if (command.kind === "cash" && paid !== total) {
    throw new ApiError(422, "PAYMENT_INCOMPLETE", "Une vente au comptant est payée en entier", {
      total,
      paid,
      remaining: total - paid,
    });
  }
}

export function checkChassis(world: World, command: RecordSaleCommand): void {
  command.lines.forEach((line) => {
    (line.details ?? []).forEach((detail) => {
      const chassis = detail.chassis_number ?? null;
      if (chassis === null) return;
      const sale = world.soldChassis.get(chassis);
      if (sale === undefined) return;
      throw new ApiError(409, "DUPLICATE", "Numéro de châssis déjà vendu", {
        field: "chassis_number",
        value: chassis,
        sale_number: sale,
      });
    });
  });
}

/** Plafond de crédit : refus pour le vendeur, avertissement pour le propriétaire (UC-VEN-02). */
export function creditLimitWarning(
  world: World,
  shopId: string,
  command: RecordSaleCommand,
  remaining: number,
): SaleWarning | null {
  const id = command.customer?.id ?? null;
  const customer = world.customers.find((known) => known.id === id);
  if (command.kind !== "credit" || customer === undefined) return null;
  if (customer.credit_limit === null) return null;
  if (customer.debt + remaining <= customer.credit_limit) return null;
  const message = `Plafond de crédit dépassé pour ${customer.name}`;
  const details = {
    customer_id: customer.id,
    limit: customer.credit_limit,
    due_before: customer.debt,
    due_after: customer.debt + remaining,
  };
  if (world.options.roleIn(shopId) === "owner") {
    return { code: "CREDIT_LIMIT_EXCEEDED", message, details };
  }
  throw new ApiError(422, "CREDIT_LIMIT_EXCEEDED", message, details);
}
