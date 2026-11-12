/**
 * Passerelle réelle des pièces jointes : `POST /api/v1/shops/{shop_id}/attachments` (multipart)
 * et `GET …/attachments/{id}/url`. Appels authentifiés par `session.authorized` ; rien n'est
 * avalé (`ApiError`, `NetworkError` remontent à l'écran, qui garde le fichier pour réessayer).
 *
 * `useAttachments()` : passerelle injectée (tests) ou, à défaut, celle des services de
 * l'application — aucun fournisseur à ajouter dans les routes existantes.
 */
import { createContext, useContext } from "react";
import { ServicesContext } from "../services/servicesContext";
import type { AppServices } from "../services/createServices";
import type { AttachmentsGateway } from "./attachmentsContract";

const SHOP = "/api/v1/shops/{shop_id}/attachments";
const CUSTOMER = "/api/v1/shops/{shop_id}/customers/{customer_id}";
const RECEIVABLE = "/api/v1/shops/{shop_id}/receivables/{receivable_id}";

export function createHttpAttachments({ api, session }: AppServices): AttachmentsGateway {
  return {
    upload: (shopId, request) => {
      const form = new FormData();
      form.append("file", request.file, request.fileName);
      form.append("owner_type", request.ownerType);
      form.append("kind", request.kind);
      form.append("id", request.id);
      if (request.ownerId !== null) form.append("owner_id", request.ownerId);
      return session.authorized((token) =>
        api.postForm(SHOP, { token, params: { shop_id: shopId }, form }),
      );
    },
    link: async (shopId, attachmentId) => {
      const issued = await session.authorized((token) =>
        api.get(`${SHOP}/{attachment_id}/url`, {
          token,
          params: { shop_id: shopId, attachment_id: attachmentId },
        }),
      );
      return {
        url: api.href(issued.url),
        expiresAt: new Date(issued.expires_at),
        mime: issued.mime,
        kind: issued.kind,
      };
    },
    linkToCustomer: async (shopId, customerId, attachmentId) => {
      const params = { shop_id: shopId, customer_id: customerId };
      await session.authorized(async (token) => {
        const sheet = await api.get(CUSTOMER, { token, params });
        const body = { version: sheet.customer.version, id_doc_photo_id: attachmentId };
        return api.patch(CUSTOMER, { token, params, body });
      });
    },
    linkToReceivable: (shopId, receivableId, attachmentId) => {
      const params = { shop_id: shopId, receivable_id: receivableId };
      return session.authorized(async (token) => {
        const current = await api.get(RECEIVABLE, { token, params });
        const ids = [...current.attachment_ids.filter((id) => id !== attachmentId), attachmentId];
        const body = { version: current.version, attachment_ids: ids };
        return api.patch(RECEIVABLE, { token, params, body });
      });
    },
  };
}

const byServices = new WeakMap<AppServices, AttachmentsGateway>();

export const AttachmentsContext = createContext<AttachmentsGateway | null>(null);

/** Passerelle injectée, sinon celle des services ; ni l'une ni l'autre : erreur de câblage. */
export function useAttachments(): AttachmentsGateway {
  const injected = useContext(AttachmentsContext);
  const services = useContext(ServicesContext);
  if (injected !== null) return injected;
  if (services === null) {
    throw new Error("useAttachments : ni AttachmentsContext ni ServicesProvider au-dessus");
  }
  let gateway = byServices.get(services);
  if (gateway === undefined) {
    gateway = createHttpAttachments(services);
    byServices.set(services, gateway);
  }
  return gateway;
}
