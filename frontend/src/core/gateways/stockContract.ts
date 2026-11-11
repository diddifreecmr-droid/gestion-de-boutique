/**
 * Passerelle des écrans Stock (specs § 4.6, § 6.3 « Stock ») : l'écran dépend de cette
 * interface, jamais de `fetch`. Tous les types viennent du contrat **généré** (schema.gen.ts) ;
 * ce que chaque rôle a le droit de voir est filtré ensuite par `features/stock/stockView.ts`.
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type StockMatrix = Schemas["StockMatrixResponse"];
export type StockColumn = Schemas["StockColumn"];
export type StockRow = Schemas["StockRow"];
export type MatrixOrder = Schemas["MatrixOrder"];
export type StockValue = Schemas["StockValueResponse"];
export type Valuation = Schemas["Valuation"];
export type LocationValuation = Schemas["LocationValuation"];
export type DamagedStock = Schemas["DamagedStockResponse"];
export type DamagedLine = Schemas["DamagedLine"];
export type MovementPage = Schemas["MovementListResponse"];
export type Movement = Schemas["MovementResponse"];
export type AdjustmentRequest = Schemas["AdjustmentRequest"];
export type Adjustment = Schemas["AdjustmentResponse"];
export type Inventory = Schemas["InventoryResponse"];
export type InventoryLine = Schemas["InventoryLineResponse"];
export type CountsRequest = Schemas["CountsRequest"];
export type ValidateRequest = Schemas["ValidateRequest"];
export type StockMember = Schemas["MemberResponse"];

/** Critères de `GET /stock` : texte (dès la 1re lettre), lieu (une colonne), tri. */
export interface MatrixQuery {
  text: string;
  locationId: string | null;
  sort: MatrixOrder;
}

export interface StockGateway {
  matrix(shopId: string, query: MatrixQuery): Promise<StockMatrix>;
  /** Propriétaire et comptable (le vendeur reçoit 403). */
  value(shopId: string): Promise<StockValue>;
  damaged(shopId: string): Promise<DamagedStock>;
  movements(shopId: string, articleId: string, cursor: string | null): Promise<MovementPage>;
  /** Nom affiché d'un article (en-tête de la fiche stock). */
  articleName(shopId: string, articleId: string): Promise<string>;
  adjust(shopId: string, body: AdjustmentRequest): Promise<Adjustment>;
  startInventory(shopId: string, id: string, locationId: string): Promise<Inventory>;
  inventory(shopId: string, inventoryId: string): Promise<Inventory>;
  saveCounts(shopId: string, inventoryId: string, body: CountsRequest): Promise<Inventory>;
  validateInventory(shopId: string, inventoryId: string, body: ValidateRequest): Promise<Inventory>;
  abandonInventory(shopId: string, inventoryId: string, version: number): Promise<Inventory>;
  /** Propriétaire seulement (`MEMBER_MANAGE`) : noms des auteurs des mouvements. */
  members(shopId: string): Promise<StockMember[]>;
}
