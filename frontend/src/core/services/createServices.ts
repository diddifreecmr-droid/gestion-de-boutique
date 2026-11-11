/** Assemblage des services de l'application (client API, session, réseau). */
import { createAuthApi } from "../api/auth";
import { createApiClient, type ApiClient } from "../api/client";
import { deviceLabel, readDeviceId } from "../api/device";
import { Session } from "../auth/session";
import { createConnectivity, type Connectivity } from "../offline/connectivity";

export interface AppServices {
  /** Client HTTP typé ; les appels authentifiés passent par `session.authorized`. */
  api: ApiClient;
  session: Session;
  connectivity: Connectivity;
}

export interface ServicesOptions {
  base?: string | undefined;
  fetch?: typeof fetch;
  window?: Window;
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
  return { api: client, session, connectivity };
}
