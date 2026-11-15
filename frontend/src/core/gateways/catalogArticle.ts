/**
 * Assemblage d'un article vu par l'écran de vente (`ArticleResponse` + ligne de `GET /stock`),
 * sans rien inventer. Quand le stock est réservé au gérant (décision du 2026-11-15), l'acteur
 * n'a pas `GET /stock` : l'article porte seulement la pastille `stock_status`, aucun chiffre.
 */
import type { components } from "../api/schema.gen";
import type { CatalogArticle, StockStatus } from "./catalogContract";
import type { SaleMode } from "./salesContract";

type Article = components["schemas"]["ArticleResponse"];
type StockRow = components["schemas"]["StockRow"];
type Profile = components["schemas"]["ProfileResponse"];

/** Ce que le profil servi dit du stock pour l'acteur. */
export interface StockPolicy {
  /** Stock réservé au gérant et acteur employé : pastille seule, aucun chiffre. */
  hidden: boolean;
  /** La vente passe même sans stock (`refused_when_out_of_stock` faux). */
  sellsWithoutStock: boolean;
}

export const COUNTED_STOCK: StockPolicy = { hidden: false, sellsWithoutStock: false };

/**
 * Politique de stock de l'acteur. Le serveur retire `STOCK_READ` au seul employé (`seller`)
 * d'un profil `stock_reserved_to_owner` (`security/role_matrix.py`, `OWNER_ONLY_STOCK`).
 */
export function stockPolicyOf(profile: Profile): StockPolicy {
  return {
    hidden: profile.stock_reserved_to_owner && profile.role === "seller",
    sellsWithoutStock: !profile.refused_when_out_of_stock,
  };
}

/** Mot de l'unité selon le profil (« Couleur — moto 1 ») ; « unité » par défaut. */
const UNIT_WORDS: Readonly<Record<string, string>> = { motos: "moto" };

export function unitWord(profileCode: string): string {
  return UNIT_WORDS[profileCode] ?? "unité";
}

/**
 * `stock_unit` de l'API (« UNIT », « PIECE », « METER ») → mode de vente par défaut de la ligne
 * (serveur, `application/sales/lines.py` : « à l'unité » pour Unité et Pièce).
 */
export function saleModeOf(stockUnit: string): SaleMode {
  const unit = stockUnit.toLowerCase();
  if (unit === "unit" || unit === "piece") return "unit";
  if (unit === "meter") return "meter";
  throw new Error(`Unité de stock inconnue : « ${stockUnit} »`);
}

function availableAt(row: StockRow | undefined, locationId: string): string {
  if (row === undefined) return "0";
  const cell = row.cells.find((c) => c.location_id === locationId);
  if (cell === undefined) throw new Error(`Stock : colonne « ${locationId} » absente de la ligne`);
  return cell.sellable;
}

/** Pastille servie à l'employé ; son absence est une rupture de contrat (fail-fast). */
function servedStatus(article: Article): StockStatus {
  const status = article.stock_status;
  if (status === "ok" || status === "low" || status === "out") return status;
  throw new Error(`« ${article.display_name} » : pastille de stock absente (GET /articles)`);
}

function stockOf(
  article: Article,
  row: StockRow | undefined,
  locationId: string,
  policy: StockPolicy,
): Pick<CatalogArticle, "available" | "stock_status" | "sells_without_stock"> {
  const sells = policy.sellsWithoutStock ? { sells_without_stock: true as const } : {};
  if (policy.hidden) return { available: null, stock_status: servedStatus(article), ...sells };
  return { available: availableAt(row, locationId), ...sells };
}

export function toCatalogArticle(
  article: Article,
  row: StockRow | undefined,
  locationId: string,
  unitLabel: string,
  policy: StockPolicy = COUNTED_STOCK,
): CatalogArticle {
  const minActive = article.min_price_active !== false;
  const length = article.piece_length_m;
  const saleMode = saleModeOf(article.stock_unit);
  if (article.sold_by_piece && (saleMode !== "meter" || length === null)) {
    throw new Error(`« ${article.display_name} » : vente au rouleau sans longueur au mètre`);
  }
  return {
    id: article.id,
    name: article.display_name,
    sale_mode: saleMode,
    unit_label: unitLabel,
    base_price: article.base_price ?? null,
    min_price: minActive ? (article.min_price ?? null) : null,
    ...stockOf(article, row, locationId, policy),
    ...(length === null ? {} : { piece_length_m: length }),
    ...(article.sold_by_piece && length !== null
      ? {
          piece: {
            length_m: length,
            base_price: article.base_price_piece ?? null,
            min_price: minActive ? (article.min_price_piece ?? null) : null,
          },
        }
      : {}),
  };
}
