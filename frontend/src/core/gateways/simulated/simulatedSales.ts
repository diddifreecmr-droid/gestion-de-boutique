/**
 * Passerelle des ventes simulée (vitrine `/_ui`) : mêmes réponses et mêmes refus que
 * `POST /sales` (§ 6.4). La liste, la fiche et le reçu servent les ventes de la session ;
 * demandes de prix : `simulatedPriceRequests.ts`. Annuler, signaler une erreur et les retours
 * n'existent pas dans la vitrine (erreur explicite).
 */
import type { CustomerSummary, SaleResult, SalesGateway } from "../salesContract";
import { normalize } from "./simulatedCatalog";
import { receiptOf, saleOf } from "./saleRecord";
import {
  checkChassis,
  checkPayments,
  checkShape,
  checkStock,
  creditLimitWarning,
  locationOf,
  paymentsOf,
  saleTotal,
} from "./saleRules";
import {
  checkApproval,
  minimumWarnings,
  consumeApproval,
  createSimulatedPriceRequests,
} from "./simulatedPriceRequests";
import { reach, requireArticle, saleNumber, type World } from "./world";

function unavailable(what: string): never {
  throw new Error(`Simulation : « ${what} » n'existe pas dans la vitrine`);
}

export function createSimulatedSales(world: World): SalesGateway {
  const printed = new Map<string, number>();
  const find = (id: string): SaleResult => {
    const found = world.sales.get(id);
    if (found === undefined) throw new Error(`Simulation : vente inconnue « ${id} »`);
    return found.result;
  };
  return {
    async recordSale(shopId, command, capturedAt) {
      await reach(world);
      const replay = world.sales.get(command.id ?? "");
      if (replay !== undefined) return replay.result; // idempotent : même id, même vente
      checkShape(command);
      checkStock(world, command);
      const approved = checkApproval(world, shopId, command);
      checkChassis(world, command);
      const total = saleTotal(command);
      checkPayments(command, total);
      const paid = paymentsOf(command).reduce((sum, payment) => sum + payment.amount, 0);
      const warning = creditLimitWarning(world, shopId, command, total - paid);

      const number = saleNumber(world.nextNumber);
      world.nextNumber += 1;
      const location = locationOf(command);
      command.lines.forEach((line) => {
        const article = requireArticle(world, line.article_id);
        const quantity = Number(line.quantity);
        article.stock[location] = (article.stock[location] ?? 0) - quantity;
        if (article.listed_at_garoua !== undefined) article.listed_at_garoua -= quantity;
        (line.details ?? []).forEach((detail) => {
          const chassis = detail.chassis_number ?? null;
          if (chassis !== null) world.soldChassis.set(chassis, number);
        });
      });
      const warnings = [
        ...minimumWarnings(world, shopId, command),
        ...(warning === null ? [] : [warning]),
      ];
      const result = saleOf(world, command, {
        number,
        total,
        paid,
        warnings,
        at: capturedAt.toISOString(),
      });
      world.sales.set(result.id, { command, result });
      if (approved) consumeApproval(world, command, result.id);
      return result;
    },

    ...createSimulatedPriceRequests(world),

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
        .map((customer) => {
          const summary: Partial<typeof customer> = { ...customer };
          delete summary.debt; // dette : donnée interne de la simulation, absente de l'API
          return summary as CustomerSummary;
        });
      return { items };
    },

    async listSales() {
      await reach(world);
      const items = [...world.sales.values()].map((entry) => entry.result).reverse();
      const total = items.reduce((sum, sale) => sum + sale.total, 0);
      const paid = items.reduce((sum, sale) => sum + sale.paid, 0);
      const counts = { count: items.length, total, paid };
      return { items, next_cursor: null, first_day: null, last_day: null, totals: counts };
    },
    async getSale(_shopId, id) {
      await reach(world);
      return find(id);
    },
    async receipt(_shopId, id) {
      await reach(world);
      const sequence = (printed.get(id) ?? 0) + 1;
      printed.set(id, sequence);
      return receiptOf(find(id), sequence);
    },
    cancelSale: () => unavailable("annuler une vente"),
    reportError: () => unavailable("signaler une erreur"),
    recordReturn: () => unavailable("enregistrer un retour"),
    listReturns: () => unavailable("lire les retours"),
    members: () => Promise.resolve([]),
  };
}
