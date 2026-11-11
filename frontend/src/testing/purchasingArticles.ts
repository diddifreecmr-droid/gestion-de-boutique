/** Articles du catalogue des tests des Achats et recherche simulée (tests seulement). */
import type { ArticleResponse } from "../core/gateways/catalogAdminContract";
import { ownerArticle, YAMAHA_ID } from "./catalog";
import { json, SHOP_A, type Reply } from "./fakeApi";

type Routes = Record<string, Reply | Reply[]>;
const API = `/api/v1/shops/${SHOP_A}`;
export const WAX_ID = "01890a5d-ac96-774b-bcce-b302099a8103";

/** Articles du catalogue (unité en majuscules, comme l'API réelle). */
export const ARTICLES: ArticleResponse[] = [
  ownerArticle({ stock_unit: "UNIT" }),
  ownerArticle({
    id: YAMAHA_ID,
    display_name: "Yamaha YBR125",
    brand: "Yamaha",
    model: "YBR125",
    stock_unit: "UNIT",
  }),
  ownerArticle({
    id: WAX_ID,
    display_name: "Wax hollandais",
    brand: "Vlisco",
    model: "Wax",
    stock_unit: "METER",
    sold_by_piece: true,
    piece_length_m: "5.5",
  }),
];

/**
 * Ajoute la recherche d'articles (`GET /articles?q=…`) : toute frappe est servie par un filtre
 * sur `articles`. À appliquer en dernier (un `...` d'un Proxy perdrait la recherche).
 */
export function withArticleSearch(routes: Routes, articles: ArticleResponse[] = ARTICLES): Routes {
  const prefix = `GET ${API}/articles?`;
  return new Proxy(routes, {
    get(target, key) {
      if (typeof key !== "string" || !key.startsWith(prefix) || key in target) {
        return Reflect.get(target, key) as unknown;
      }
      const q = (new URLSearchParams(key.slice(prefix.length)).get("q") ?? "").toLowerCase();
      const items = articles.filter((a) => a.display_name.toLowerCase().includes(q));
      return json(200, { items, next_cursor: null });
    },
  });
}
