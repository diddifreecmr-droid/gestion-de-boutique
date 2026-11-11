/** Catalogue simulé : recherche dès la 1re lettre, « plus vendus » d'abord (CDC § 1.3). */
import type { CatalogArticle, CatalogGateway } from "../catalogContract";
import { GAROUA, PAYMENT_MODES, type SeedArticle } from "./seed";
import { reach, type World } from "./world";

/** Compare sans accents ni casse : « nan » trouve « Nanfang ». */
export function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

function byRankThenName(a: SeedArticle, b: SeedArticle): number {
  const rankA = a.rank ?? Number.MAX_SAFE_INTEGER;
  const rankB = b.rank ?? Number.MAX_SAFE_INTEGER;
  return rankA === rankB ? a.name.localeCompare(b.name, "fr") : rankA - rankB;
}

/** Vue de l'article pour le client : jamais de coût (TR-05), minimum seulement s'il est partagé. */
function present(article: SeedArticle & { stock: Record<string, number> }, locationId: string) {
  const real = article.stock[locationId];
  if (real === undefined) throw new Error(`Simulation : lieu inconnu « ${locationId} »`);
  const listed = locationId === GAROUA.id ? (article.listed_at_garoua ?? real) : real;
  const view: CatalogArticle = {
    id: article.id,
    name: article.name,
    sale_mode: "unit",
    unit_label: "moto",
    base_price: article.base_price,
    min_price: article.min_price_shared ? article.min_price : null,
    available: String(listed),
  };
  return view;
}

export function createSimulatedCatalog(world: World): CatalogGateway {
  return {
    async saleSetup() {
      await reach(world);
      return { location: GAROUA, payment_modes: PAYMENT_MODES.map((mode) => ({ ...mode })) };
    },
    async searchArticles(_shopId, search) {
      await reach(world);
      if (!Number.isSafeInteger(search.limit) || search.limit < 1) {
        throw new Error(`Simulation : limite de recherche invalide (${String(search.limit)})`);
      }
      const query = normalize(search.query.trim());
      const all = [...world.articles.values()];
      const matches =
        query === ""
          ? all.filter((article) => article.rank !== null)
          : all.filter((article) => normalize(article.name).includes(query));
      return {
        items: matches
          .sort(byRankThenName)
          .slice(0, search.limit)
          .map((article) => present(article, search.location_id)),
      };
    },
  };
}
