import { describe, expect, it } from "vitest";
import {
  ATTACHMENT_ID,
  attachment,
  CONTENT_URL,
  LINK,
  linkBody,
  UPLOAD,
} from "../../testing/attachments";
import { signedIn } from "../../testing/catalog";
import { createFakeFetch, json, SHOP_A, type Reply } from "../../testing/fakeApi";
import { receivable } from "../../testing/receivables";
import { createServices } from "../services/createServices";
import { createHttpAttachments } from "./httpAttachments";

const API = `/api/v1/shops/${SHOP_A}`;

async function gateway(extra: Record<string, Reply>) {
  const fake = createFakeFetch({ ...signedIn("seller"), ...extra });
  const services = createServices({ base: "/api", fetch: fake.fetch });
  await services.session.restore();
  return { fake, attachments: createHttpAttachments(services) };
}

describe("passerelle HTTP des pièces jointes", () => {
  it("envoie le fichier en multipart avec l'élément lié, le type et l'identifiant client", async () => {
    const { fake, attachments } = await gateway({ [UPLOAD]: json(201, attachment()) });
    const file = new Blob(["%PDF-1.4"], { type: "application/pdf" });
    const sent = await attachments.upload(SHOP_A, {
      id: ATTACHMENT_ID,
      ownerType: "receivable",
      ownerId: "sale-124",
      kind: "id_document",
      file,
      fileName: "cni.pdf",
    });
    expect(sent.id).toBe(ATTACHMENT_ID);
    const call = fake.calls.find((c) => `${c.method} ${c.url}` === UPLOAD);
    expect(call?.headers.get("Authorization")).toBe("Bearer t1");
    expect(call?.headers.get("Content-Type")).toBeNull(); // borne posée par le navigateur
    const form = call?.form;
    expect([form?.get("owner_type"), form?.get("owner_id"), form?.get("kind")]).toEqual([
      "receivable",
      "sale-124",
      "id_document",
    ]);
    expect(form?.get("id")).toBe(ATTACHMENT_ID);
    expect((form?.get("file") as File).name).toBe("cni.pdf");
  });

  it("sans élément lié, `owner_id` n'est pas envoyé", async () => {
    const { fake, attachments } = await gateway({ [UPLOAD]: json(201, attachment()) });
    const request = { id: ATTACHMENT_ID, ownerType: "expense" as const, ownerId: null };
    await attachments.upload(SHOP_A, {
      ...request,
      kind: "receipt",
      file: new Blob(["x"]),
      fileName: "ticket.jpg",
    });
    expect(fake.calls.at(-1)?.form?.has("owner_id")).toBe(false);
  });

  it("le lien court devient une URL du navigateur (même origine, préfixe de VITE_API_BASE)", async () => {
    const { attachments } = await gateway({ [LINK]: json(200, linkBody()) });
    const link = await attachments.link(SHOP_A, ATTACHMENT_ID);
    expect(link.url).toBe(CONTENT_URL.replace("/api/", "/api/"));
    expect(link.url.startsWith("/api/v1/shops/")).toBe(true);
    expect(link.expiresAt.toISOString()).toBe("2026-11-11T10:01:00.000Z");
    expect([link.mime, link.kind]).toEqual(["image/jpeg", "id_document"]);
  });

  it("rattache la photo au client (version relue) et à la créance (sans doublon)", async () => {
    const customer = `${API}/customers/cust-1`;
    const sheet = {
      customer: { id: "cust-1", version: 4 },
      total_bought: 0,
      total_due: 0,
      sales: [],
    };
    const current = receivable({ version: 7, attachment_ids: ["a-1", ATTACHMENT_ID] });
    const { fake, attachments } = await gateway({
      [`GET ${customer}`]: json(200, sheet),
      [`PATCH ${customer}`]: json(200, sheet.customer),
      [`GET ${API}/receivables/sale-124`]: json(200, current),
      [`PATCH ${API}/receivables/sale-124`]: json(200, current),
    });
    await attachments.linkToCustomer(SHOP_A, "cust-1", ATTACHMENT_ID);
    expect(fake.calls.find((c) => c.method === "PATCH")?.body).toEqual({
      version: 4,
      id_doc_photo_id: ATTACHMENT_ID,
    });
    await attachments.linkToReceivable(SHOP_A, "sale-124", ATTACHMENT_ID);
    expect(fake.calls.at(-1)?.body).toEqual({ version: 7, attachment_ids: ["a-1", ATTACHMENT_ID] });
  });
});
