/**
 * Passerelle **réelle** du catalogue de l'écran de vente : elle assemble les réponses de
 * l'API sans rien inventer.
 *
 * - `saleSetup` : `GET /profile` (lieu habituel, profil), `GET /payment-modes` (actifs) et
 *   `GET /stock` pour les colonnes « point de vente » (le vendeur ne lit pas `/locations`, Q-30).
 * - `searchArticles` : `GET /articles?sort=best_selling&status=active&q=&limit=` (plus vendus
 *   sur 30 jours, puis par nom) **et** `GET /stock?q=&location_id=` (stock du lieu de vente),
 *   joints par `article_id` ; un article sans ligne de stock au lieu a 0.
 * - Stock réservé au gérant (2026-11-15) : l'employé n'a pas `GET /stock` (403). Il vend depuis
 *   son lieu habituel et ne reçoit que la pastille `stock_status` de `GET /articles`.
 */
import type { AppServices } from "../services/createServices";
import type { components } from "../api/schema.gen";
import { stockPolicyOf, toCatalogArticle, unitWord, type StockPolicy } from "./catalogArticle";
import type { CatalogGateway, SaleLocation } from "./catalogContract";

export { saleModeOf, toCatalogArticle, unitWord } from "./catalogArticle";

type Profile = components["schemas"]["ProfileResponse"];
type StockMatrix = components["schemas"]["StockMatrixResponse"];

const SHOP = "/api/v1/shops/{shop_id}";

/** Nom affiché du lieu habituel quand l'acteur ne lit pas la liste des lieux. */
export const USUAL_PLACE = "votre point de vente";

interface ShopRules {
  unit: string;
  policy: StockPolicy;
}

function pointsOfSale(matrix: StockMatrix): SaleLocation[] {
  return matrix.locations
    .filter((column) => column.is_point_of_sale)
    .map((column) => ({ id: column.location_id, name: column.name }));
}

export function createHttpCatalog({ api, session, offline }: AppServices): CatalogGateway {
  const shop = (shopId: string) => ({ shop_id: shopId });
  const rules = new Map<string, ShopRules>();
  const profileOf = async (shopId: string): Promise<Profile> => {
    const profile = await session.authorized((token) =>
      api.get(`${SHOP}/profile`, { token, params: shop(shopId) }),
    );
    rules.set(shopId, { unit: unitWord(profile.profile_code), policy: stockPolicyOf(profile) });
    offline.rights.note(shopId, profile.entitlements); // droit hors connexion (T23, TR-26)
    return profile;
  };
  const rulesOf = async (shopId: string): Promise<ShopRules> => {
    const known = rules.get(shopId);
    if (known !== undefined) return known;
    await profileOf(shopId);
    const loaded = rules.get(shopId);
    if (loaded === undefined) throw new Error(`Profil de la boutique ${shopId} non chargé`);
    return loaded;
  };
  const locationsOf = async (shopId: string, profile: Profile): Promise<SaleLocation[]> => {
    if (!stockPolicyOf(profile).hidden) {
      const matrix = await session.authorized((token) =>
        api.get(`${SHOP}/stock`, { token, params: shop(shopId) }),
      );
      return pointsOfSale(matrix);
    }
    const usual = profile.default_location_id;
    return usual === null ? [] : [{ id: usual, name: USUAL_PLACE }];
  };
  return {
    saleSetup: async (shopId) => {
      const [profile, modes] = await Promise.all([
        profileOf(shopId),
        session.authorized((token) =>
          api.get(`${SHOP}/payment-modes`, { token, params: shop(shopId) }),
        ),
      ]);
      return {
        locations: await locationsOf(shopId, profile),
        default_location_id: profile.default_location_id,
        min_price_requires_approval: profile.min_price_requires_approval,
        payment_modes: modes
          .filter((mode) => mode.active)
          .sort((a, b) => a.display_order - b.display_order),
        article_fields: profile.article_fields.map(({ code, label }) => ({ code, label })),
        sale_fields: profile.sale_fields.map((field) => field.code),
        sale_shortcuts: profile.sale_shortcuts,
        piece_label: profile.piece_label,
      };
    },
    searchArticles: async (shopId, { location_id, query, limit }) => {
      const q = query.trim() === "" ? null : query.trim();
      const { unit, policy } = await rulesOf(shopId);
      const [articles, matrix] = await Promise.all([
        session.authorized((token) =>
          api.get(`${SHOP}/articles`, {
            token,
            params: shop(shopId),
            query: { q, status: "active", sort: "best_selling", limit },
          }),
        ),
        policy.hidden
          ? Promise.resolve(null)
          : session.authorized((token) =>
              api.get(`${SHOP}/stock`, { token, params: shop(shopId), query: { q, location_id } }),
            ),
      ]);
      const rows = new Map((matrix?.items ?? []).map((row) => [row.article_id, row]));
      return {
        items: articles.items.map((article) =>
          toCatalogArticle(article, rows.get(article.id), location_id, unit, policy),
        ),
      };
    },
  };
}
