/**
 * Chiffres de la page d'accueil minimale (specs § 15.1, « Page d'accueil ») : total des ventes
 * du jour et 5 dernières ventes, lus dans `GET /sales` du jour (le serveur ne renvoie au vendeur
 * que **ses** ventes, RG-D02). Seuls numéro, client, montant et heure sont gardés : aucun coût
 * ni marge ne sort d'ici, quel que soit le rôle.
 */
import type { Customer, CustomersGateway } from "../../core/gateways/customersContract";
import type { SaleResult, SalesGateway } from "../../core/gateways/salesContract";

/** Nombre de ventes affichées sous le total (décision client). */
export const RECENT_LIMIT = 5;
/** Vente sans client. */
export const CASH_CUSTOMER = "Comptant";

export interface RecentSale {
  id: string;
  number: string;
  /** Nom du client, ou « Comptant ». */
  customer: string;
  total: number;
  soldAt: string;
  cancelled: boolean;
  credit: boolean;
}

export interface TodaySales {
  /** Total du jour calculé par le serveur (annulations du jour déduites). */
  total: number;
  count: number;
  recent: RecentSale[];
}

async function customerNames(
  customers: CustomersGateway,
  shopId: string,
  sales: readonly SaleResult[],
): Promise<Map<string, string>> {
  if (sales.every((sale) => sale.customer_id === null)) return new Map();
  const found: Customer[] = await customers.search(shopId, "");
  return new Map(found.map((customer) => [customer.id, customer.name]));
}

function recentOf(sale: SaleResult, names: Map<string, string>): RecentSale {
  let customer = CASH_CUSTOMER;
  if (sale.customer_id !== null) {
    const name = names.get(sale.customer_id);
    if (name === undefined) {
      throw new Error(`Client ${sale.customer_id} de la vente ${sale.number} introuvable`);
    }
    customer = name;
  }
  return {
    id: sale.id,
    number: sale.number,
    customer,
    total: sale.total,
    soldAt: sale.sold_at,
    cancelled: sale.status === "cancelled",
    credit: sale.kind === "credit",
  };
}

/** Une seule page du jour (plus récentes en haut) ; les noms des clients en une lecture. */
export async function loadTodaySales(
  gateways: { sales: SalesGateway; customers: CustomersGateway },
  shopId: string,
): Promise<TodaySales> {
  const page = await gateways.sales.listSales(shopId, {}, null);
  const latest = page.items.slice(0, RECENT_LIMIT);
  const names = await customerNames(gateways.customers, shopId, latest);
  return {
    total: page.totals.total,
    count: page.totals.count,
    recent: latest.map((sale) => recentOf(sale, names)),
  };
}
