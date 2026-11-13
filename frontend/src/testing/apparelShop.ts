/**
 * Faux serveur d'une boutique **Prêt-à-porter** ou **Textile** (tests seulement, VOC-01, T39) :
 * un seul lieu « Boutique » (QC-5), articles du profil, aucune donnée Motos. Les routes de la
 * boutique sont servies par chemin (la requête est ignorée) ; une route non prévue fait échouer
 * le test, comme le faux serveur des ventes.
 */
import type { components } from "../core/api/schema.gen";
import type { Role } from "../core/auth/me";
import { ownerArticle } from "./catalog";
import { dashboardBody, homeBody } from "./dashboard";
import { json, meBody, ROUTES, SHOP_A, tokenBody, type Reply } from "./fakeApi";
import { paymentModes } from "./salesCatalog";
import { page } from "./salesFixtures";
import { member } from "./salesServer";
import { servedProfile } from "./servedProfile";

type Schemas = components["schemas"];
type Routes = Record<string, Reply | Reply[]>;
export type ShopRole = "owner" | "seller";
export type ApparelCode = "apparel" | "textile";

export const API = `/api/v1/shops/${SHOP_A}`;
export const STORE_ID = "01890a5d-ac96-774b-bcce-b302099a8211";
export const ARTICLE_ID = "01890a5d-ac96-774b-bcce-b302099a8111";
const OWNER_ID = "01890a5d-ac96-774b-bcce-b302099a8000";
const SELLER_ID = "01890a5d-ac96-774b-bcce-b302099a8010";

/** Article de la boutique, vu par le rôle (le vendeur ne reçoit aucun coût, TR-05). */
function article(code: ApparelCode, role: ShopRole): Schemas["ArticleResponse"] {
  const raw: Partial<Schemas["ArticleResponse"]> =
    code === "apparel"
      ? ownerArticle({
          id: ARTICLE_ID,
          display_name: "Chemise lin",
          brand: null,
          model: null,
          stock_unit: "PIECE",
          attributes: { category: "Chemises" },
          base_price: 15000,
          min_price: 12000,
        })
      : ownerArticle({
          id: ARTICLE_ID,
          display_name: "Wax Fleur de mariage",
          brand: null,
          model: null,
          stock_unit: "METER",
          sold_by_piece: true,
          piece_length_m: "5.49",
          attributes: {},
          base_price: 2500,
          base_price_piece: 13000,
          min_price: null,
        });
  if (role === "seller") {
    delete raw.last_cost;
    delete raw.wac;
    delete raw.price_history;
  }
  return raw as Schemas["ArticleResponse"];
}

function matrix(code: ApparelCode, role: ShopRole): Schemas["StockMatrixResponse"] {
  const one = article(code, role);
  const quantity = code === "apparel" ? "6.000" : "46.900";
  const row: Schemas["StockRow"] = {
    article_id: one.id,
    display_name: one.display_name,
    stock_unit: one.stock_unit,
    cells: [{ location_id: STORE_ID, sellable: quantity, damaged: "0.000" }],
    incoming: "0.000",
    total: quantity,
    stock_status: "ok",
    alert_threshold: "2",
    base_price: one.base_price ?? null,
    ...(role === "owner" ? { last_cost: 9000, wac: 9000, wac_value: 54000 } : {}),
  };
  return {
    locations: [{ location_id: STORE_ID, name: "Boutique", kind: "shop", is_point_of_sale: true }],
    items: [row],
  };
}

function profile(code: ApparelCode, role: ShopRole): Schemas["ProfileResponse"] {
  const served = servedProfile(code, role);
  return {
    ...served,
    default_location_id: role === "seller" ? STORE_ID : null,
    receipt: {
      ...served.receipt,
      header: { ...served.receipt.header, name: "Mode Maroua", city: "Maroua" },
    },
  };
}

/** Réponse d'une route de la boutique, par méthode et chemin (sans la requête). */
function serve(code: ApparelCode, role: ShopRole, method: string, path: string): Response | null {
  if (method !== "GET") return null;
  if (path === "/profile") return json(200, profile(code, role));
  if (path === "/payment-modes") return json(200, paymentModes());
  if (path === "/stock") return json(200, matrix(code, role));
  if (path === "/articles") return json(200, { items: [article(code, role)], next_cursor: null });
  if (path === `/articles/${ARTICLE_ID}`) return json(200, article(code, role));
  if (path === "/sales") return json(200, page([]));
  if (path === "/members") {
    return json(200, [
      member(OWNER_ID, "Aïssatou Bello", "owner"),
      member(SELLER_ID, "Issa", "seller"),
    ]);
  }
  if (path === "/price-requests") return json(200, []);
  if (path === "/customers") return json(200, []);
  if (path === "/dashboard") return json(200, dashboardBody());
  if (path === "/home") return json(200, homeBody("seller"));
  return null;
}

/** Session de `role` dans « Mode Maroua » (profil `code`) et routes de la boutique. */
export function apparelShop(code: ApparelCode, role: ShopRole): Routes {
  const base: Routes = {
    [ROUTES.refresh]: json(200, tokenBody("t1")),
    [ROUTES.me]: json(
      200,
      meBody({
        user_id: role === "owner" ? OWNER_ID : SELLER_ID,
        shops: [{ shop_id: SHOP_A, shop_name: "Mode Maroua", role: role }],
      }),
    ),
  };
  return new Proxy(base, {
    get(target, key) {
      if (typeof key !== "string" || key in target) return Reflect.get(target, key) as unknown;
      const at = key.indexOf(` ${API}`);
      if (at < 0) return undefined;
      const method = key.slice(0, at);
      const path = (key.slice(at + 1 + API.length).split("?")[0] ?? "").replace(/\/$/, "");
      const reply = serve(code, role, method, path);
      if (reply === null) return undefined;
      const answer: Reply = () => reply.clone();
      return answer;
    },
  });
}
