/**
 * Pièces jointes pour les tests : réponses du faux serveur, fichiers d'exemple, codec d'image
 * factice (jsdom n'a ni `createImageBitmap` ni canvas). Réservé aux tests.
 */
import type { Attachment } from "../core/gateways/attachmentsContract";
import type { ImageCodec } from "../features/attachments/prepareFile";
import { SHOP_A } from "./fakeApi";

export const ATTACHMENT_ID = "01890a5d-ac96-774b-bcce-b302099a9001";
export const UPLOAD = `POST /api/v1/shops/${SHOP_A}/attachments`;
export const LINK = `GET /api/v1/shops/${SHOP_A}/attachments/${ATTACHMENT_ID}/url`;
export const CONTENT_URL = `/api/v1/shops/${SHOP_A}/attachments/${ATTACHMENT_ID}/content?expires=1794384060&signature=sig`;

export function attachment(overrides: Partial<Attachment> = {}): Attachment {
  return {
    id: ATTACHMENT_ID,
    owner_type: "receivable",
    owner_id: "sale-124",
    kind: "id_document",
    mime: "image/jpeg",
    size_bytes: 120_000,
    uploaded_at: "2026-11-11T10:00:00Z",
    ...overrides,
  };
}

export function linkBody(mime: Attachment["mime"] = "image/jpeg") {
  return { url: CONTENT_URL, expires_at: "2026-11-11T10:01:00Z", mime, kind: "id_document" };
}

export const pdfFile = () =>
  new File(["%PDF-1.4 cni"], "CNI recto.pdf", { type: "application/pdf" });
export const photoFile = () => new File(["photo"], "IMG_0001.HEIC", { type: "image/heic" });

/** Codec qui « réduit » toute image en un JPEG de `size` octets. */
export function fakeCodec(size = 200_000): ImageCodec & { calls: number[] } {
  const calls: number[] = [];
  return {
    calls,
    reduce: (_file, maxSide) => {
      calls.push(maxSide);
      return Promise.resolve(new Blob([new Uint8Array(size)], { type: "image/jpeg" }));
    },
  };
}
