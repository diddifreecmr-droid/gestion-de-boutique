/**
 * Faux serveur de la vente **Textile** (tests seulement), au-dessus du faux serveur des ventes :
 * profil Textile avec ses raccourcis (RG-X05), un seul lieu « Boutique » (QC-5), articles au
 * mètre (jeu de la recette SCN-L3-02 : WX, pièce de 5,49 m) et `POST /sales` au dixième (QC-3) :
 * stock retiré, refus `422 STOCK_INSUFFICIENT` (`available` en mètres), reçu `quantity_label`.
 */
import type { components } from "../core/api/schema.gen";
import type { RecordSaleCommand, SaleResult } from "../core/gateways/salesContract";
import { tenthsValue, toTenths } from "../features/sales/textile";
import { ownerArticle } from "./catalog";
import { apiError, json, type Call } from "./fakeApi";
import { saleReceipt } from "./receipts";
import { paymentModes, saleProfile } from "./salesCatalog";
import { API, saleServer, type SaleRole } from "./salesServer";
import { servedProfile } from "./servedProfile";
import { quantityLabel, removedBy, saleResult, type TextileArticle } from "./textileSaleResult";

export type { TextileArticle } from "./textileSaleResult";

type Schemas = components["schemas"];

export const BOUTIQUE = { id: "loc-boutique", name: "Boutique" };

/** Raccourcis servis par `GET /profile` d'une boutique Textile (`domain/profiles/textile.py`). */
export const TEXTILE_SHORTCUTS: Schemas["SaleShortcutResponse"][] = [
  { code: "piece", label: "Pièce complète", basis: "piece", length_m: null, yards: "6" },
  { code: "half_piece", label: "Demi-pièce", basis: "half_piece", length_m: null, yards: "3" },
  { code: "1m", label: "1 m", basis: "length", length_m: "1.0", yards: null },
  { code: "2m", label: "2 m", basis: "length", length_m: "2.0", yards: null },
  { code: "3m", label: "3 m", basis: "length", length_m: "3.0", yards: null },
];

/** WX « Wax Fleur de mariage » : 10 pièces achetées = 54,9 m, 2 500 le mètre, 13 000 la pièce. */
export const WX: TextileArticle = {
  id: "art-wx",
  name: "Wax Fleur de mariage",
  stock: "54.9",
  piece_length_m: "5.49",
  sold_by_piece: true,
  base_price: 2500,
  base_price_piece: 13000,
};

/** Tissu au mètre seulement, sans longueur de pièce (raccourcis sur 6 yards). */
export const BAZIN: TextileArticle = {
  id: "art-bazin",
  name: "Bazin riche",
  stock: "12.0",
  piece_length_m: null,
  sold_by_piece: false,
  base_price: 4000,
  base_price_piece: null,
};

function textileProfile(role: SaleRole) {
  return {
    ...servedProfile("textile", role),
    default_location_id: role === "seller" ? BOUTIQUE.id : null,
    min_price_requires_approval: false,
    sale_shortcuts: TEXTILE_SHORTCUTS,
    receipt: saleProfile(role).receipt,
  };
}

/** Vue de l'employé : prix de vente seulement, aucun coût (TR-05). */
function articleView(article: TextileArticle): Schemas["ArticleResponse"] {
  const raw: Partial<Schemas["ArticleResponse"]> = ownerArticle({
    id: article.id,
    display_name: article.name,
    brand: null,
    model: null,
    stock_unit: "METER",
    sold_by_piece: article.sold_by_piece,
    piece_length_m: article.piece_length_m,
    attributes: {},
    base_price: article.base_price,
    base_price_piece: article.base_price_piece,
    min_price: null,
    min_price_piece: null,
  });
  delete raw.last_cost;
  delete raw.wac;
  return raw as Schemas["ArticleResponse"];
}

function matrix(articles: readonly TextileArticle[]): Schemas["StockMatrixResponse"] {
  return {
    locations: [
      { location_id: BOUTIQUE.id, name: BOUTIQUE.name, kind: "shop", is_point_of_sale: true },
    ],
    items: articles.map((article) => ({
      article_id: article.id,
      display_name: article.name,
      stock_unit: "METER",
      cells: [{ location_id: BOUTIQUE.id, sellable: article.stock, damaged: "0.0" }],
      incoming: "0.0",
      total: article.stock,
      stock_status: "ok" as const,
      alert_threshold: "1.0",
      base_price: article.base_price,
    })),
  };
}

/** Routes du faux serveur Textile pour `role`, sur les articles donnés. */
export function textileWorld(role: SaleRole, articles: TextileArticle[]) {
  const server = saleServer(role, { [`GET ${API}/profile`]: json(200, textileProfile(role)) });
  const byId = new Map(articles.map((article) => [article.id, article]));
  const sales: SaleResult[] = [];
  const article = (id: string) => {
    const found = byId.get(id);
    if (found === undefined) throw new Error(`Faux serveur Textile : article ${id}`);
    return found;
  };
  const record = (call: Call) => {
    const body = call.body as RecordSaleCommand;
    server.recordSale("shop", body);
    for (const line of body.lines) {
      const sold = article(line.article_id);
      const stock = toTenths(sold.real ?? sold.stock);
      if (removedBy(sold, line) > stock) {
        const details = { article_id: sold.id, available: tenthsValue(stock), other_locations: [] };
        return apiError(422, "STOCK_INSUFFICIENT", "Stock insuffisant", details);
      }
    }
    const sale = saleResult(body, byId, sales.length + 1);
    sales.push(sale);
    return json(201, sale);
  };
  const receipt = (call: Call) => {
    const sale = sales.find((one) => call.url.includes(one.id));
    if (sale === undefined) throw new Error("Faux serveur : reçu d'une vente inconnue");
    const lines = sale.lines.map((line) => ({
      ...line,
      quantity_label: quantityLabel(article(line.article_id), line.sale_mode, line.quantity),
    }));
    const body = saleReceipt({ sale_id: sale.id, number: sale.number, lines, total: sale.total });
    return json(200, body);
  };
  const routes = new Proxy(server.routes, {
    get(target, key) {
      if (typeof key !== "string") return Reflect.get(target, key) as unknown;
      if (key.startsWith(`GET ${API}/articles`)) {
        return json(200, { items: articles.map(articleView), next_cursor: null });
      }
      if (key.startsWith(`GET ${API}/stock`)) return json(200, matrix(articles));
      if (key === `GET ${API}/payment-modes`) return json(200, paymentModes());
      if (key === `POST ${API}/sales`) return record;
      if (key.startsWith(`GET ${API}/sales/`) && key.endsWith("/receipt")) return receipt;
      return Reflect.get(target, key) as unknown;
    },
  });
  return { server, routes, sales };
}
