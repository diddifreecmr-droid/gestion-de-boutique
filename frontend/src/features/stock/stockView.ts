/**
 * Ligne de stock **vue par un rôle** (TR-05, RG-D02, CDC § 4.2, UC-STK-05). L'écran ne lit
 * jamais `StockRow` directement : ce module recopie seulement ce que le rôle a le droit de voir,
 * même si le serveur en envoyait plus (défense en profondeur).
 *
 * | Vue | Quantités | Prix de base | Coûts (dernier coût, CMP, valeur) |
 * | --- | --- | --- | --- |
 * | `owner` | oui | oui | oui |
 * | `accountant` | oui | **non** | oui |
 * | `seller` | oui | oui | **le type n'a pas de champ de coût** |
 */
import type { StockColumn, StockRow } from "../../core/gateways/stockContract";
import type { StockRole } from "./stockRoles";

export type StockStatus = "ok" | "low" | "out";

export interface StockPlace {
  locationId: string;
  name: string;
  sellable: string;
  damaged: string;
}

export interface StockLineCore {
  articleId: string;
  name: string;
  unit: string;
  /** Un lieu par colonne, dans l'ordre d'affichage des lieux. */
  places: readonly StockPlace[];
  incoming: string;
  total: string;
  status: StockStatus;
}

/** `null` = « non calculable » (aucun achat encore, RG-T15). */
export interface StockCosts {
  lastCost: number | null;
  wac: number | null;
  /** Vendable × CMP. */
  value: number | null;
}

export interface OwnerStockLine extends StockLineCore {
  kind: "owner";
  basePrice: number | null;
  costs: StockCosts;
}

export interface AccountantStockLine extends StockLineCore {
  kind: "accountant";
  costs: StockCosts;
}

export interface SellerStockLine extends StockLineCore {
  kind: "seller";
  basePrice: number | null;
}

export type StockLine = OwnerStockLine | AccountantStockLine | SellerStockLine;

function contractError(field: string, role: StockRole): never {
  throw new Error(`Contrat du stock rompu : « ${field} » absent pour le rôle ${role}`);
}

function amount(raw: StockRow, key: keyof StockRow, role: StockRole): number | null {
  if (!(key in raw)) contractError(key, role);
  const value = raw[key];
  if (value === null) return null;
  if (typeof value !== "number" || !Number.isSafeInteger(value)) contractError(key, role);
  return value;
}

function status(raw: StockRow): StockStatus {
  const value: string = raw.stock_status;
  if (value === "ok" || value === "low" || value === "out") return value;
  throw new Error(`Pastille de stock inconnue : « ${value} »`);
}

function core(raw: StockRow, columns: readonly StockColumn[]): StockLineCore {
  const places = columns.map((column) => {
    const cell = raw.cells.find((candidate) => candidate.location_id === column.location_id);
    if (cell === undefined) {
      throw new Error(`Case absente : « ${raw.display_name} » au lieu « ${column.name} »`);
    }
    return {
      locationId: column.location_id,
      name: column.name,
      sellable: cell.sellable,
      damaged: cell.damaged,
    };
  });
  return {
    articleId: raw.article_id,
    name: raw.display_name,
    unit: raw.stock_unit,
    places,
    incoming: raw.incoming,
    total: raw.total,
    status: status(raw),
  };
}

function costs(raw: StockRow, role: StockRole): StockCosts {
  return {
    lastCost: amount(raw, "last_cost", role),
    wac: amount(raw, "wac", role),
    value: amount(raw, "wac_value", role),
  };
}

export function stockLine(
  role: StockRole,
  raw: StockRow,
  columns: readonly StockColumn[],
): StockLine {
  switch (role) {
    case "owner":
      return {
        ...core(raw, columns),
        kind: "owner",
        basePrice: amount(raw, "base_price", role),
        costs: costs(raw, role),
      };
    case "accountant":
      return { ...core(raw, columns), kind: "accountant", costs: costs(raw, role) };
    case "seller":
      return { ...core(raw, columns), kind: "seller", basePrice: amount(raw, "base_price", role) };
  }
}

export function basePriceOf(line: StockLine): number | null | undefined {
  return line.kind === "accountant" ? undefined : line.basePrice;
}

export function costsOf(line: StockLine): StockCosts | null {
  return line.kind === "seller" ? null : line.costs;
}
