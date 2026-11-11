/**
 * Passerelle réelle du Tableau de bord : routes `/api/v1/shops/{shop_id}/…` (T19), appels
 * authentifiés par `session.authorized` (refresh unique puis rejeu). Rien n'est avalé :
 * `ApiError` et `NetworkError` remontent à l'écran. Aucune réponse n'est gardée en mémoire :
 * chaque affichage relit le serveur (RG-T25, les chiffres ne viennent jamais d'un cache).
 */
import type { AppServices } from "../services/createServices";
import type { PeriodQuery, ReportingGateway } from "./reportingContract";

const DASHBOARD = "/api/v1/shops/{shop_id}/dashboard";
const DETAIL = "/api/v1/shops/{shop_id}/dashboard/details/{metric}";
const HOME = "/api/v1/shops/{shop_id}/home";

/** `?period=…` ; `from` / `to` ne partent qu'avec la période libre (le serveur refuse sinon). */
export function periodParams(query: PeriodQuery): Record<string, string> {
  if (query.period !== "custom") return { period: query.period };
  if (query.from === "" || query.to === "") {
    throw new Error("Période libre incomplète : « du » et « au » sont obligatoires");
  }
  return { period: query.period, from: query.from, to: query.to };
}

export function createHttpReporting({ api, session }: AppServices): ReportingGateway {
  return {
    dashboard: (shopId, period) =>
      session.authorized((token) =>
        api.get(DASHBOARD, { token, params: { shop_id: shopId }, query: periodParams(period) }),
      ),
    detail: (shopId, metric, period) =>
      session.authorized((token) =>
        api.get(DETAIL, {
          token,
          params: { shop_id: shopId, metric },
          query: periodParams(period),
        }),
      ),
    home: (shopId) =>
      session.authorized((token) => api.get(HOME, { token, params: { shop_id: shopId } })),
  };
}
