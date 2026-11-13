/**
 * Catalogue du faux serveur des ventes (tests seulement) : `/profile`, `/payment-modes`,
 * `/stock`, `/articles` servis depuis le monde simulé (`core/gateways/simulated/seed.ts`),
 * dans les formes **générées** de l'API (quantités « 4.000 », unité « UNIT »).
 */
import type { components } from "../core/api/schema.gen";
import { normalize } from "../core/gateways/simulated/simulatedCatalog";
import { BOULAI, GAROUA, LOCATIONS, PAYMENT_MODES } from "../core/gateways/simulated/seed";
import type { World } from "../core/gateways/simulated/world";
import { ownerArticle, profileBody } from "./catalog";

type Schemas = components["schemas"];
type WorldArticle = World["articles"] extends Map<string, infer A> ? A : never;

const decimal = (value: number) => `${String(value)}.000`;

/** Champs de vente du profil Motos (`GET /profile`) : couleur, châssis, moteur. */
const MOTOS_SALE_FIELDS = [
  ["color", "Couleur"],
  ["chassis_number", "Numéro de châssis"],
  ["engine_number", "Numéro de moteur"],
] as const;

export function saleProfile(role: "owner" | "seller", requiresApproval = false) {
  return {
    ...profileBody(role),
    default_location_id: role === "seller" ? GAROUA.id : null,
    min_price_requires_approval: requiresApproval,
    sale_fields: MOTOS_SALE_FIELDS.map(([code, label]) => ({
      code,
      label,
      kind: "text",
      required: false,
      unique: code === "chassis_number",
      choices: [],
    })),
  };
}

/** Profil « Prêt-à-porter » vu par l'écran de vente : ni modèle ni châssis. */
export function apparelSaleProfile(role: "owner" | "seller") {
  const field = (code: string, label: string) => ({
    code,
    label,
    kind: "text",
    required: code === "name",
    unique: false,
    choices: [],
  });
  return {
    ...saleProfile(role),
    profile_code: "apparel",
    profile_label: "Prêt-à-porter",
    article_fields: [
      field("name", "Nom"),
      field("reference", "Référence"),
      field("type", "Type"),
      field("brand", "Marque"),
    ],
    sale_fields: [field("size", "Taille"), field("color", "Couleur")],
  };
}

export const paymentModes = () => PAYMENT_MODES.map((mode) => ({ ...mode }));

/** Stock affiché à Garoua (le catalogue peut être en retard sur le réel, cf. seed). */
function listed(article: WorldArticle, locationId: string): number {
  const real = article.stock[locationId] ?? 0;
  return locationId === GAROUA.id ? (article.listed_at_garoua ?? real) : real;
}

function matches(article: WorldArticle, q: string | null): boolean {
  return q === null || normalize(article.name).includes(normalize(q));
}

export function stockMatrix(world: World, q: string | null): Schemas["StockMatrixResponse"] {
  const locations = LOCATIONS.map((place) => ({
    location_id: place.id,
    name: place.name,
    kind: place.id === BOULAI.id ? "warehouse" : "shop",
    is_point_of_sale: place.id !== BOULAI.id,
  }));
  const items = [...world.articles.values()]
    .filter((article) => matches(article, q))
    .map((article) => {
      const total = LOCATIONS.reduce((sum, place) => sum + listed(article, place.id), 0);
      return {
        article_id: article.id,
        display_name: article.name,
        stock_unit: "UNIT",
        cells: LOCATIONS.map((place) => ({
          location_id: place.id,
          sellable: decimal(listed(article, place.id)),
          damaged: "0.000",
        })),
        incoming: "0.000",
        total: decimal(total),
        stock_status: total > 0 ? ("ok" as const) : ("out" as const),
        alert_threshold: "2.000",
        base_price: article.base_price,
      };
    });
  return { locations, items };
}

/** Vue vendeur d'un article : prix de vente seulement, jamais de coût (TR-05). */
function sellerArticle(article: WorldArticle): Schemas["ArticleResponse"] {
  const raw: Partial<Schemas["ArticleResponse"]> = ownerArticle({
    id: article.id,
    display_name: article.name,
    stock_unit: "UNIT",
    base_price: article.base_price,
    min_price: article.min_price_shared ? article.min_price : null,
    min_price_active: article.min_price_shared ? true : null,
  });
  delete raw.last_cost;
  delete raw.wac;
  return raw as Schemas["ArticleResponse"];
}

/** `GET /articles?sort=best_selling` : classés d'abord (rang), puis par nom. */
export function articleList(world: World, q: string | null, limit: number) {
  const rank = (a: WorldArticle) => a.rank ?? Number.MAX_SAFE_INTEGER;
  const items = [...world.articles.values()]
    .filter((article) => matches(article, q))
    .sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name, "fr"))
    .slice(0, limit)
    .map(sellerArticle);
  return { items, next_cursor: null };
}
