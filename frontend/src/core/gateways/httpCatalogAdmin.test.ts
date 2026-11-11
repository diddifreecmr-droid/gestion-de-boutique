import { describe, expect, it } from "vitest";
import { API, catalogRoutes, HAOJUE_ID, listUrl, ownerArticle } from "../../testing/catalog";
import { createFakeFetch, json, SHOP_A, type Reply } from "../../testing/fakeApi";
import { fillPath, queryString } from "../api/pathParams";
import { createServices } from "../services/createServices";
import { appCatalogAdmin } from "./catalogAdminContext";

async function gateway(extra: Record<string, Reply>) {
  const fake = createFakeFetch(catalogRoutes("owner", extra));
  const services = createServices({ base: "/api", fetch: fake.fetch });
  await services.session.restore();
  return { fake, catalog: appCatalogAdmin(services), services };
}

describe("passerelle HTTP du catalogue", () => {
  it("appelle chaque route avec le jeton, la bonne méthode et le corps", async () => {
    const article = json(200, ownerArticle());
    const { fake, catalog, services } = await gateway({
      [listUrl("hao", "all", "c2")]: json(200, { items: [], next_cursor: null }),
      [`GET ${API}/articles/${HAOJUE_ID}`]: article,
      [`POST ${API}/articles`]: json(201, ownerArticle()),
      [`PATCH ${API}/articles/${HAOJUE_ID}`]: article,
      [`PUT ${API}/articles/${HAOJUE_ID}/prices`]: article,
      [`POST ${API}/articles/${HAOJUE_ID}/archive`]: article,
      [`POST ${API}/articles/${HAOJUE_ID}/reactivate`]: article,
    });
    expect(appCatalogAdmin(services)).toBe(catalog);
    const form = await catalog.articleForm(SHOP_A);
    expect(form.fields.map((f) => f.code)).toEqual(["brand", "model", "engine_cc", "category"]);
    expect(form.minPriceEnabled).toBe(true);
    await catalog.listArticles(SHOP_A, { text: " hao ", status: "all", cursor: "c2", limit: 20 });
    await catalog.getArticle(SHOP_A, HAOJUE_ID);
    expect((await catalog.createArticle(SHOP_A, { fields: {} })).id).toBe(HAOJUE_ID);
    await catalog.updateArticle(SHOP_A, HAOJUE_ID, { version: 3 });
    await catalog.setPrices(SHOP_A, HAOJUE_ID, { version: 3, base_price: 1 });
    await catalog.archiveArticle(SHOP_A, HAOJUE_ID);
    await catalog.reactivateArticle(SHOP_A, HAOJUE_ID);
    const sent = fake.calls.filter((c) => c.url.includes("/shops/"));
    expect(sent).toHaveLength(8);
    expect(sent.every((c) => c.headers.get("Authorization") === "Bearer t1")).toBe(true);
    expect(sent.find((c) => c.method === "PUT")?.body).toEqual({ version: 3, base_price: 1 });
  });
});

describe("paramètres de chemin et de requête", () => {
  it("remplit, encode et refuse un paramètre manquant ou en trop", () => {
    expect(fillPath("/a/{shop_id}/b/{article_id}", { shop_id: "s 1", article_id: "x" })).toBe(
      "/a/s%201/b/x",
    );
    expect(() => fillPath("/a/{shop_id}")).toThrow("« shop_id » absent");
    expect(() => fillPath("/a/{shop_id}", { shop_id: "" })).toThrow("absent");
    expect(() => fillPath("/a", { other: "x" })).toThrow("inconnus");
    expect(queryString({ q: null, status: "all", limit: 20, more: undefined })).toBe(
      "?status=all&limit=20",
    );
    expect(queryString()).toBe("");
  });
});
