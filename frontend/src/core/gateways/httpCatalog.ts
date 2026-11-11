/**
 * Passerelle **réelle** du catalogue de l'écran de vente : elle assemble les réponses de
 * l'API sans rien inventer.
 *
 * - `saleSetup` : `GET /profile` (lieu habituel, profil), `GET /payment-modes` (actifs) et
 *   `GET /stock` pour les colonnes « point de vente » (le vendeur ne lit pas `/locations`, Q-30).
 * - `searchArticles` : `GET /articles?sort=best_selling&status=active&q=&limit=` (plus vendus
 *   sur 30 jours, puis par nom) **et** `GET /stock?q=&location_id=` (stock du lieu de vente),
 *   joints par `article_id` ; un article sans ligne de stock au lieu a 0.
 */
import type { AppServices } from "../services/createServices";
import type { components } from "../api/schema.gen";
import type { CatalogArticle, CatalogGateway } from "./catalogContract";
import type { SaleMode } from "./salesContract";

type Article = components["schemas"]["ArticleResponse"];
type StockRow = components["schemas"]["StockRow"];

const SHOP = "/api/v1/shops/{shop_id}";

/** Mot de l'unité selon le profil (« Couleur — moto 1 ») ; « unité » par défaut. */
const UNIT_WORDS: Readonly<Record<string, string>> = { motos: "moto" };

export function unitWord(profileCode: string): string {
  return UNIT_WORDS[profileCode] ?? "unité";
}

/** `stock_unit` de l'API (« UNIT », « METER ») → mode de vente de la ligne. */
export function saleModeOf(stockUnit: string): SaleMode {
  const unit = stockUnit.toLowerCase();
  if (unit === "unit") return "unit";
  if (unit === "meter") return "meter";
  throw new Error(`Unité de stock inconnue : « ${stockUnit} »`);
}

function availableAt(row: StockRow | undefined, locationId: string): string {
  if (row === undefined) return "0";
  const cell = row.cells.find((c) => c.location_id === locationId);
  if (cell === undefined) throw new Error(`Stock : colonne « ${locationId} » absente de la ligne`);
  return cell.sellable;
}

export function toCatalogArticle(
  article: Article,
  row: StockRow | undefined,
  locationId: string,
  unitLabel: string,
): CatalogArticle {
  return {
    id: article.id,
    name: article.display_name,
    sale_mode: saleModeOf(article.stock_unit),
    unit_label: unitLabel,
    base_price: article.base_price ?? null,
    min_price: article.min_price_active === false ? null : (article.min_price ?? null),
    available: availableAt(row, locationId),
  };
}

export function createHttpCatalog({ api, session, offline }: AppServices): CatalogGateway {
  const shop = (shopId: string) => ({ shop_id: shopId });
  const units = new Map<string, string>();
  const profileOf = async (shopId: string) => {
    const profile = await session.authorized((token) =>
      api.get(`${SHOP}/profile`, { token, params: shop(shopId) }),
    );
    units.set(shopId, unitWord(profile.profile_code));
    offline.rights.note(shopId, profile.entitlements); // droit hors connexion (T23, TR-26)
    return profile;
  };
  return {
    saleSetup: async (shopId) => {
      const [profile, modes, matrix] = await Promise.all([
        profileOf(shopId),
        session.authorized((token) =>
          api.get(`${SHOP}/payment-modes`, { token, params: shop(shopId) }),
        ),
        session.authorized((token) => api.get(`${SHOP}/stock`, { token, params: shop(shopId) })),
      ]);
      return {
        locations: matrix.locations
          .filter((column) => column.is_point_of_sale)
          .map((column) => ({ id: column.location_id, name: column.name })),
        default_location_id: profile.default_location_id,
        min_price_requires_approval: profile.min_price_requires_approval,
        payment_modes: modes
          .filter((mode) => mode.active)
          .sort((a, b) => a.display_order - b.display_order),
      };
    },
    searchArticles: async (shopId, { location_id, query, limit }) => {
      const q = query.trim() === "" ? null : query.trim();
      const [articles, matrix] = await Promise.all([
        session.authorized((token) =>
          api.get(`${SHOP}/articles`, {
            token,
            params: shop(shopId),
            query: { q, status: "active", sort: "best_selling", limit },
          }),
        ),
        session.authorized((token) =>
          api.get(`${SHOP}/stock`, { token, params: shop(shopId), query: { q, location_id } }),
        ),
      ]);
      const rows = new Map(matrix.items.map((row) => [row.article_id, row]));
      const unit = units.get(shopId) ?? unitWord((await profileOf(shopId)).profile_code);
      return {
        items: articles.items.map((article) =>
          toCatalogArticle(article, rows.get(article.id), location_id, unit),
        ),
      };
    },
  };
}
