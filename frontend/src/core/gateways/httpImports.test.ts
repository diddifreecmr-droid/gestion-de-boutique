import { describe, expect, it } from "vitest";
import { ApiError } from "../api/errors";
import { signedIn } from "../../testing/catalog";
import { apiError, createFakeFetch, json, SHOP_A, type Reply } from "../../testing/fakeApi";
import { importBatch, importPreview, PREVIEW_ID } from "../../testing/imports";
import { createServices } from "../services/createServices";
import { createHttpImports } from "./httpImports";

const API = `/api/v1/shops/${SHOP_A}`;
const TEMPLATE = `GET ${API}/imports/templates/articles`;
const PREVIEW = `POST ${API}/imports/preview`;
const CONFIRM = `POST ${API}/imports`;
const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

async function gateway(extra: Record<string, Reply>) {
  const fake = createFakeFetch({ ...signedIn("owner"), ...extra });
  const services = createServices({ base: "/api", fetch: fake.fetch });
  await services.session.restore();
  return { fake, imports: createHttpImports(services) };
}

function xlsx(disposition: string | null): Response {
  const headers = new Headers({ "Content-Type": XLSX });
  if (disposition !== null) headers.set("Content-Disposition", disposition);
  return new Response("PK-modele", { status: 200, headers });
}

describe("passerelle HTTP de l'import", () => {
  it("modèle : fichier binaire et nom donné par le serveur, jeton envoyé", async () => {
    const reply = xlsx('attachment; filename="modele-articles.xlsx"');
    const { fake, imports } = await gateway({ [TEMPLATE]: reply });
    const file = await imports.template(SHOP_A, "articles");
    expect(file.fileName).toBe("modele-articles.xlsx");
    expect(await file.blob.text()).toBe("PK-modele");
    const call = fake.calls.find((c) => `${c.method} ${c.url}` === TEMPLATE);
    expect(call?.headers.get("Authorization")).toBe("Bearer t1");
    expect(call?.headers.get("Accept")).toBe("*/*");
  });

  it("modèle sans nom de fichier : nom par défaut ; refus : l'erreur de l'API remonte", async () => {
    const { imports } = await gateway({ [TEMPLATE]: xlsx(null) });
    expect((await imports.template(SHOP_A, "articles")).fileName).toBe("modele-articles.xlsx");
    const denied = await gateway({
      [TEMPLATE]: apiError(403, "MODULE_DISABLED", "Module éteint"),
    });
    await expect(denied.imports.template(SHOP_A, "articles")).rejects.toBeInstanceOf(ApiError);
  });

  it("aperçu : multipart avec le modèle et le fichier", async () => {
    const { fake, imports } = await gateway({ [PREVIEW]: json(200, importPreview()) });
    const file = new File(["nom;prix"], "articles.csv", { type: "text/csv" });
    const preview = await imports.preview(SHOP_A, "articles", file);
    expect(preview.preview_id).toBe(PREVIEW_ID);
    const form = fake.calls.find((c) => `${c.method} ${c.url}` === PREVIEW)?.form;
    expect(form?.get("kind")).toBe("articles");
    expect((form?.get("file") as File).name).toBe("articles.csv");
  });

  it("confirmation : corps `preview_id`, lot renvoyé ; 410 remonte tel quel", async () => {
    const { fake, imports } = await gateway({ [CONFIRM]: json(201, importBatch()) });
    expect((await imports.confirm(SHOP_A, PREVIEW_ID)).number).toBe("IMP-000001");
    expect(fake.calls.find((c) => `${c.method} ${c.url}` === CONFIRM)?.body).toEqual({
      preview_id: PREVIEW_ID,
    });
    const expired = await gateway({
      [CONFIRM]: apiError(410, "IMPORT_PREVIEW_EXPIRED", "Aperçu expiré"),
    });
    await expect(expired.imports.confirm(SHOP_A, PREVIEW_ID)).rejects.toMatchObject({
      status: 410,
      code: "IMPORT_PREVIEW_EXPIRED",
    });
  });
});
