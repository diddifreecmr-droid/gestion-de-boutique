/** Données et routes du faux serveur pour les écrans du Stock (tests seulement). */
import type {
  Inventory,
  InventoryLine,
  Movement,
  StockColumn,
  StockRow,
  Valuation,
} from "../core/gateways/stockContract";
import { API, HAOJUE_ID, signedIn, YAMAHA_ID } from "./catalog";
import { json, SHOP_A, type Reply } from "./fakeApi";

type Role = "owner" | "seller" | "accountant" | "driver";
type Routes = Record<string, Reply | Reply[]>;

export { API, HAOJUE_ID, YAMAHA_ID };
export const STOCK_PAGE = `/s/${SHOP_A}/stock`;
export const GAROUA = "01890a5d-ac96-774b-bcce-b302099a8201";
export const NGAOUNDERE = "01890a5d-ac96-774b-bcce-b302099a8202";
export const INVENTORY_ID = "01890a5d-ac96-774b-bcce-b302099a8301";
export const OWNER_ID = "01890a5d-ac96-774b-bcce-b302099a8000";
export const OTHER_ID = "01890a5d-ac96-774b-bcce-b302099a8009";

export const COLUMNS: StockColumn[] = [
  { location_id: GAROUA, name: "Garoua", kind: "shop", is_point_of_sale: true },
  { location_id: NGAOUNDERE, name: "Ngaoundéré", kind: "warehouse", is_point_of_sale: false },
];

/** Ligne de matrice telle que l'API l'envoie au rôle (clés de coût/prix absentes sinon). */
export function stockRow(role: Role, overrides: Partial<StockRow> = {}): StockRow {
  const row: StockRow = {
    article_id: HAOJUE_ID,
    display_name: "Haojue HJ125-8",
    stock_unit: "UNIT",
    cells: [
      { location_id: GAROUA, sellable: "1.000", damaged: "0.000" },
      { location_id: NGAOUNDERE, sellable: "0.000", damaged: "1.000" },
    ],
    incoming: "0.000",
    total: "1.000",
    stock_status: "low",
    alert_threshold: "2",
    base_price: 780000,
    last_cost: 650000,
    wac: 640000,
    wac_value: 640000,
    ...overrides,
  };
  if (role !== "owner" && role !== "accountant") {
    delete row.last_cost;
    delete row.wac;
    delete row.wac_value;
  }
  if (role === "accountant") delete row.base_price;
  return row;
}

export function emptyRow(role: Role): StockRow {
  return stockRow(role, {
    article_id: YAMAHA_ID,
    display_name: "Yamaha Crypton",
    cells: [
      { location_id: GAROUA, sellable: "0.000", damaged: "0.000" },
      { location_id: NGAOUNDERE, sellable: "0.000", damaged: "0.000" },
    ],
    total: "0.000",
    stock_status: "out",
    ...(role === "accountant" ? {} : { base_price: null }),
    ...(role === "seller" ? {} : { wac: null, last_cost: null, wac_value: null }),
  });
}

export function matrixUrl(q: string | null = null, location: string | null = null, sort = "name") {
  const params = new URLSearchParams();
  if (q !== null) params.append("q", q);
  if (location !== null) params.append("location_id", location);
  params.append("sort", sort);
  return `GET ${API}/stock?${params.toString()}`;
}

export function matrixBody(role: Role, columns: StockColumn[] = COLUMNS) {
  return { locations: columns, items: [stockRow(role), emptyRow(role)] };
}

export function stockRoutes(role: Role, extra: Routes = {}): Routes {
  return { ...signedIn(role), [matrixUrl()]: json(200, matrixBody(role)), ...extra };
}

export function movement(overrides: Partial<Movement> = {}): Movement {
  return {
    id: "01890a5d-ac96-774b-bcce-b302099a8401",
    type: "purchase_in",
    type_label: "Entrée achat",
    location_id: GAROUA,
    location_name: "Garoua",
    condition: "sellable",
    quantity: "2.000",
    balance_after: "2.000",
    document: { type: "purchase", id: "p1", number: "A-000001" },
    occurred_at: "2026-11-10T13:32:00Z",
    recorded_at: "2026-11-10T13:32:00Z",
    author_id: OTHER_ID,
    stock_to_verify: false,
    reverses_id: null,
    ...overrides,
  };
}

export function inventoryLine(overrides: Partial<InventoryLine> = {}): InventoryLine {
  return {
    article_id: HAOJUE_ID,
    display_name: "Haojue HJ125-8",
    stock_unit: "UNIT",
    counted: null,
    ...overrides,
  };
}

export function inventory(overrides: Partial<Inventory> = {}): Inventory {
  return {
    id: INVENTORY_ID,
    number: "INV-000001",
    version: 1,
    status: "in_progress",
    location_id: GAROUA,
    location_name: "Garoua",
    started_at: "2026-11-10T08:00:00Z",
    closed_at: null,
    global_reason: null,
    sales_since_start: 0,
    sales_message: null,
    counted_lines: 0,
    lines: [
      inventoryLine(),
      inventoryLine({ article_id: YAMAHA_ID, display_name: "Yamaha Crypton" }),
    ],
    ...overrides,
  };
}

export function valuation(overrides: Partial<Valuation> = {}): Valuation {
  return {
    at_wac: 1280000,
    at_wac_known: 1280000,
    without_wac: 0,
    at_last_cost: 1300000,
    at_last_cost_known: 1300000,
    without_last_cost: 0,
    ...overrides,
  };
}

/** Inventaire validé : un écart (−1, CMP inconnu), un article sans écart. */
export function validatedInventory(): Inventory {
  return inventory({
    version: 3,
    status: "validated",
    closed_at: "2026-11-10T15:00:00Z",
    global_reason: "Casse",
    gap_count: 1,
    gap_value: null,
    lines: [
      inventoryLine({
        counted: "1.000",
        theoretical: "2.000",
        difference: "-1.000",
        reason: "Casse",
        gap_value: null,
      }),
      inventoryLine({
        article_id: YAMAHA_ID,
        display_name: "Yamaha Crypton",
        counted: "0.000",
        theoretical: "0.000",
        difference: "0.000",
        reason: null,
        gap_value: 0,
      }),
    ],
  });
}
