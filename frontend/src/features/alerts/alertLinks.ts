/**
 * Élément lié à une alerte (ALR-02) : l'appui ouvre la vente, l'article, la créance, la demande
 * de prix… **dans un écran que le rôle peut ouvrir**. Sans écran pour ce rôle (ou type inconnu),
 * aucun lien n'est proposé : on n'envoie jamais un utilisateur vers une page interdite.
 * De même pour l'écran d'un module éteint (specs § 15.1).
 */
import type { Role } from "../../core/auth/me";
import type { AlertEntity } from "../../core/gateways/alertsContract";
import type { ModuleCode, ShopModules } from "../../core/profile/modules";
import { shopPath } from "../../core/profile/shopProfile";
import { articlePath } from "../catalog/catalogPaths";
import { STOCK_KEY } from "../catalog/catalogRights";
import { EXPENSES_KEY } from "../expenses/expenseNav";
import { PURCHASES_KEY } from "../purchasing/purchasingNav";
import { RECEIVABLES_KEY } from "../receivables/receivablesNav";
import { MY_SALES_KEY, PRICE_REQUESTS_KEY, SALES_KEY } from "../sales/salesNav";

/** Section « Clients » (« Plus → Clients » du propriétaire). */
export const CUSTOMERS_KEY = "clients";

type Linker = (shopId: string, id: string, role: Role) => string | null;

const q = (id: string) => encodeURIComponent(id);
const managers: readonly Role[] = ["owner", "accountant"];

const LINKERS: Readonly<Record<string, Linker>> = {
  sale: (shopId, id, role) => {
    if (role === "owner") return `${shopPath(shopId, SALES_KEY)}?id=${q(id)}`;
    if (role === "seller") return `${shopPath(shopId, MY_SALES_KEY)}?id=${q(id)}`;
    return null;
  },
  receivable: (shopId, id, role) =>
    role === "owner" || role === "seller"
      ? `${shopPath(shopId, RECEIVABLES_KEY)}?vue=fiche&id=${q(id)}`
      : null,
  price_request: (shopId, _id, role) =>
    role === "owner" ? shopPath(shopId, PRICE_REQUESTS_KEY) : null,
  article: (shopId, id, role) =>
    managers.includes(role) ? articlePath(shopId, id) : shopPath(shopId, STOCK_KEY),
  inventory: (shopId, id, role) =>
    managers.includes(role) ? `${shopPath(shopId, STOCK_KEY)}?vue=inventaire&id=${q(id)}` : null,
  purchase: (shopId, id, role) =>
    managers.includes(role) ? `${shopPath(shopId, PURCHASES_KEY)}?vue=fiche&id=${q(id)}` : null,
  expense: (shopId, id, role) =>
    managers.includes(role) ? `${shopPath(shopId, EXPENSES_KEY)}?vue=fiche&id=${q(id)}` : null,
  customer: (shopId, id, role) =>
    role === "owner" ? `${shopPath(shopId, CUSTOMERS_KEY)}?id=${q(id)}` : null,
};

/** Module de l'écran ouvert par le lien (les autres types relèvent de modules toujours actifs). */
const MODULE_OF: Readonly<Record<string, ModuleCode>> = {
  receivable: "receivables",
  purchase: "purchases",
  expense: "expenses",
};

/** Adresse de l'élément lié, ou `null` s'il n'y a rien à ouvrir pour ce rôle et ces modules. */
export function entityLink(
  shopId: string,
  entity: AlertEntity,
  role: Role,
  modules: ShopModules,
): string | null {
  if (entity.id === null) return null;
  const module = MODULE_OF[entity.type];
  if (module !== undefined && !modules.has(module)) return null;
  const linker = LINKERS[entity.type];
  return linker === undefined ? null : linker(shopId, entity.id, role);
}
