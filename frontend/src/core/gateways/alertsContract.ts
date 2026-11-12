/**
 * Passerelle des Alertes (UC-SOC-09, specs § 6.3) : l'écran dépend de cette interface, jamais
 * de `fetch`. Types issus du contrat **généré**.
 *
 * Droits (serveur) : chacun ne reçoit que **ses** alertes dans la boutique active ; marquer
 * l'alerte d'un autre → 404 (ALR-03). Le message est rédigé par la règle du module, sans
 * donnée interdite à son destinataire (aucun coût pour un vendeur).
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type Alert = Schemas["AlertResponse"];
export type AlertPage = Schemas["AlertPageResponse"];
export type AlertEntity = Schemas["EntityResponse"];

export interface AlertQuery {
  unreadOnly: boolean;
  cursor: string | null;
}

export interface AlertsGateway {
  /** `GET /alerts` : les plus récentes en haut, avec le nombre de non lues. */
  list(shopId: string, query: AlertQuery): Promise<AlertPage>;
  /** `POST /alerts/{id}/read` : « traitée » ; renvoie le nombre de non lues restantes. */
  markRead(shopId: string, alertId: string): Promise<number>;
}
