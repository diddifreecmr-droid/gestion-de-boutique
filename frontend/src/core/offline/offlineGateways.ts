/**
 * Choix **API ou file** des deux saisies possibles hors connexion au Lot 1 (RG-T22, specs
 * § 6.5) : `SalesGateway.recordSale` et `ExpensesGateway.record`. Les autres méthodes restent
 * celles de la passerelle réelle.
 *
 * - Droit `offline_capture` **inactif** (V1) : l'appel part comme avant ; un échec réseau
 *   devient `OfflineNotAllowed` (sous-classe de `NetworkError` : « Connexion nécessaire »,
 *   aucune mise en file, Dexie jamais chargé — recette OFF-01, OFF-03).
 * - Droit **actif** : sans réseau (ou si l'envoi échoue faute de réseau), la saisie entre dans
 *   la file avec son `id` client comme `op_id`, et l'écran reçoit un document provisoire.
 *   Toute autre erreur (`ApiError`…) remonte telle quelle.
 */
import { BUSINESS_TIME_ZONE } from "../../shared/format";
import { NetworkError } from "../api/errors";
import { uuidV7 } from "../api/uuidv7";
import type { ExpensesGateway } from "../gateways/expensesContract";
import type { SalesGateway } from "../gateways/salesContract";
import type { AppServices } from "../services/createServices";
import type { OfflineCapture } from "./capture";
import type { Connectivity } from "./connectivity";
import { OfflineNotAllowed } from "./errors";
import { provisionalExpense, provisionalSale } from "./provisionalDocs";

export interface OfflineDeps {
  offline: OfflineCapture;
  connectivity: Connectivity;
  deviceId: () => string;
  /** Jour métier « AAAA-MM-JJ » (Douala) d'un instant. */
  today: (at: Date) => string;
}

/** Jour métier « AAAA-MM-JJ » à Douala. */
export function businessDayOf(at: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: BUSINESS_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(at);
}

export function offlineDeps({ offline, connectivity }: AppServices): OfflineDeps {
  return { offline, connectivity, deviceId: offline.deviceId, today: businessDayOf };
}

async function apiOrQueue<T>(
  deps: OfflineDeps,
  shopId: string,
  online: () => Promise<T>,
  queued: () => Promise<T>,
): Promise<T> {
  const allowed = deps.offline.enabled(shopId);
  if (allowed && !deps.connectivity.online) return queued();
  try {
    return await online();
  } catch (error) {
    if (!(error instanceof NetworkError)) throw error;
    if (!allowed) throw new OfflineNotAllowed({ cause: error });
    return queued();
  }
}

export function withOfflineSales(gateway: SalesGateway, deps: OfflineDeps): SalesGateway {
  const queueSale: SalesGateway["recordSale"] = async (shopId, command, capturedAt) => {
    const id = command.id ?? uuidV7();
    const snapshot = await deps.offline.snapshot(shopId);
    // Instantané jamais lu (RG-T25) : sans noms d'articles, pas de reçu provisoire possible.
    if (snapshot === null) throw new OfflineNotAllowed();
    const number = await deps.offline.queue({
      shopId,
      opId: id,
      type: "sale.create",
      capturedAt,
      payload: { ...command, id },
    });
    return provisionalSale(command, snapshot, {
      id,
      number,
      capturedAt,
      deviceId: deps.deviceId(),
      today: deps.today(capturedAt),
    });
  };
  return {
    ...gateway,
    recordSale: (shopId, command, capturedAt) =>
      apiOrQueue(
        deps,
        shopId,
        () => gateway.recordSale(shopId, command, capturedAt),
        () => queueSale(shopId, command, capturedAt),
      ),
  };
}

export function withOfflineExpenses(gateway: ExpensesGateway, deps: OfflineDeps): ExpensesGateway {
  const queueExpense: ExpensesGateway["record"] = async (shopId, body) => {
    const id = body.id ?? uuidV7();
    const capturedAt = new Date();
    const number = await deps.offline.queue({
      shopId,
      opId: id,
      type: "expense.create",
      capturedAt,
      payload: { ...body, id },
    });
    return provisionalExpense(body, {
      id,
      number,
      capturedAt,
      deviceId: deps.deviceId(),
      today: deps.today(capturedAt),
    });
  };
  return {
    ...gateway,
    record: (shopId, body) =>
      apiOrQueue(
        deps,
        shopId,
        () => gateway.record(shopId, body),
        () => queueExpense(shopId, body),
      ),
  };
}
