/** Passerelle des ventes simulée : mêmes réponses et mêmes refus que `POST /sales` (§ 6.4). */
import type { SaleResult, SalesGateway } from "../salesContract";
import { normalize } from "./simulatedCatalog";
import {
  checkChassis,
  checkMinimum,
  checkPayments,
  checkShape,
  checkStock,
  creditLimitWarning,
  saleTotal,
} from "./saleRules";
import { reach, requireArticle, saleNumber, type World } from "./world";

const PRICE_REQUEST_TTL_MS = 30 * 60_000;

export function createSimulatedSales(world: World): SalesGateway {
  return {
    async recordSale(shopId, command) {
      await reach(world);
      const replay = world.sales.get(command.id);
      if (replay !== undefined) return replay.result; // idempotent : même id, même vente
      checkShape(command);
      checkStock(world, command);
      checkMinimum(world, shopId, command);
      checkChassis(world, command);
      const total = saleTotal(command);
      checkPayments(command, total);
      const paid = command.payments.reduce((sum, payment) => sum + payment.amount, 0);
      const remaining = total - paid;
      const warning = creditLimitWarning(world, shopId, command, remaining);

      const number = saleNumber(world.nextNumber);
      world.nextNumber += 1;
      const lines = command.lines.map((line) => {
        const article = requireArticle(world, line.article_id);
        const quantity = Number(line.quantity);
        article.stock[command.location_id] = (article.stock[command.location_id] ?? 0) - quantity;
        if (article.listed_at_garoua !== undefined) article.listed_at_garoua -= quantity;
        line.details.forEach((detail) => {
          if (detail.chassis_number !== null) world.soldChassis.set(detail.chassis_number, number);
        });
        return {
          article_name: article.name,
          quantity: line.quantity,
          unit_price: line.unit_price,
          line_total: quantity * line.unit_price,
        };
      });
      const result: SaleResult = {
        id: command.id,
        number,
        status: "valid",
        kind: command.kind,
        total,
        paid,
        remaining,
        receivable: command.kind === "credit" ? { id: `rec-${command.id}`, remaining } : null,
        lines,
        warnings: warning === null ? [] : [{ code: "CREDIT_LIMIT_EXCEEDED", message: warning }],
      };
      world.sales.set(command.id, { command, result });
      return result;
    },

    async requestPriceApproval(_shopId, command) {
      await reach(world);
      requireArticle(world, command.article_id);
      world.priceRequests.add(command.id);
      return {
        id: command.id,
        status: "pending",
        expires_at: new Date(Date.now() + PRICE_REQUEST_TTL_MS).toISOString(),
      };
    },

    async searchCustomers(_shopId, query) {
      await reach(world);
      const text = normalize(query.trim());
      const digits = query.replace(/\D/g, "");
      if (text === "") return { items: [] };
      const items = world.customers
        .filter(
          (customer) =>
            normalize(customer.name).includes(text) ||
            (digits.length >= 3 && customer.phone.includes(digits)),
        )
        .map(({ id, name, phone, kind }) => ({ id, name, phone, kind }));
      return { items };
    },
  };
}
