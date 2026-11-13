/**
 * Passerelle réelle de l'import : `…/imports/templates/{kind}`, `…/imports/preview`
 * (multipart) et `POST …/imports`. Appels authentifiés par `session.authorized` ; rien n'est
 * avalé (`ApiError`, `NetworkError` remontent à l'écran).
 *
 * `useImports()` : passerelle fournie par la route (ou par un test) ; absente → erreur de câblage.
 */
import { createContext, useContext } from "react";
import type { AppServices } from "../services/createServices";
import type { ImportsGateway } from "./importsContract";

const TEMPLATE = "/api/v1/shops/{shop_id}/imports/templates/{kind}";
const PREVIEW = "/api/v1/shops/{shop_id}/imports/preview";
const CONFIRM = "/api/v1/shops/{shop_id}/imports";

export function createHttpImports({ api, session }: AppServices): ImportsGateway {
  return {
    template: async (shopId, kind) => {
      const fetched = await session.authorized((token) =>
        api.getFile(TEMPLATE, { token, params: { shop_id: shopId, kind } }),
      );
      return { blob: fetched.blob, fileName: fetched.fileName ?? `modele-${kind}.xlsx` };
    },
    preview: (shopId, kind, file) => {
      const form = new FormData();
      form.append("kind", kind);
      form.append("file", file, file.name);
      return session.authorized((token) =>
        api.postForm(PREVIEW, { token, params: { shop_id: shopId }, form }),
      );
    },
    confirm: (shopId, previewId) =>
      session.authorized((token) =>
        api.post(CONFIRM, { token, params: { shop_id: shopId }, body: { preview_id: previewId } }),
      ),
  };
}

export const ImportsContext = createContext<ImportsGateway | null>(null);

/** Passerelle de l'écran d'import ; hors d'un `<ImportsContext>`, c'est une erreur de câblage. */
export function useImports(): ImportsGateway {
  const gateway = useContext(ImportsContext);
  if (gateway === null) throw new Error("useImports doit être appelé sous <ImportsContext>");
  return gateway;
}
