/** Assemblage des services de l'application (client API, session, réseau). */
import { createAuthApi } from "../api/auth";
import { createApiClient, type ApiClient } from "../api/client";
import { deviceLabel, readDeviceId } from "../api/device";
import { Session } from "../auth/session";
import { createOfflineCapture, type OfflineCapture } from "../offline/capture";
import { createConnectivity, type Connectivity } from "../offline/connectivity";
import type * as OfflineEngine from "../offline/engine";
import { createOfflineRights } from "../offline/rights";

export interface AppServices {
  /** Client HTTP typé ; les appels authentifiés passent par `session.authorized`. */
  api: ApiClient;
  session: Session;
  connectivity: Connectivity;
  /** Saisie hors connexion : inerte tant que `offline_capture` est inactif (V1, TR-26). */
  offline: OfflineCapture;
}

export interface ServicesOptions {
  base?: string | undefined;
  fetch?: typeof fetch;
  window?: Window;
  /** Chargement de la file hors connexion (tests : espion, base `fake-indexeddb`). */
  offlineEngine?: () => Promise<typeof OfflineEngine>;
}

export function createServices(options: ServicesOptions = {}): AppServices {
  const target = options.window ?? window;
  const base = options.base ?? import.meta.env.VITE_API_BASE;
  if (typeof base !== "string" || base === "") {
    throw new Error("VITE_API_BASE est absent : copiez .env.example en .env (VITE_API_BASE=/api)");
  }
  const connectivity = createConnectivity(target);
  let deviceId: string | null = null;
  const client = createApiClient({
    base,
    // Lu au premier appel (et non au démarrage) : une erreur de stockage s'affiche à l'écran.
    deviceId: () => (deviceId ??= readDeviceId()),
    onResponse: () => {
      connectivity.reportResponse();
    },
    onNetworkFailure: () => {
      connectivity.reportNetworkFailure();
    },
    ...(options.fetch === undefined ? {} : { fetch: options.fetch }),
  });
  const session = new Session(createAuthApi(client), deviceLabel(target.navigator.userAgent));
  const offline = createOfflineCapture({
    rights: createOfflineRights(() => target.localStorage),
    deviceId: () => (deviceId ??= readDeviceId()),
    send: (shopId, body) =>
      session.authorized((token) =>
        client.post("/api/v1/shops/{shop_id}/sync", { token, params: { shop_id: shopId }, body }),
      ),
    fetchSnapshot: (shopId) =>
      session.authorized((token) =>
        client.get("/api/v1/shops/{shop_id}/offline-snapshot", {
          token,
          params: { shop_id: shopId },
        }),
      ),
    ...(options.offlineEngine === undefined ? {} : { load: options.offlineEngine }),
  });
  return { api: client, session, connectivity, offline };
}
