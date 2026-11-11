import { NetworkError } from "../api/errors";

/**
 * Saisie impossible sans réseau : le droit `offline_capture` n'est pas ouvert pour la
 * boutique (TR-26, V1). Hérite de `NetworkError` : les écrans affichent « Connexion
 * nécessaire » exactement comme avant T23 (recette OFF-01, OFF-03).
 */
export class OfflineNotAllowed extends NetworkError {
  constructor(options?: ErrorOptions) {
    super("Connexion nécessaire : saisie hors connexion non ouverte pour cette boutique", options);
    this.name = "OfflineNotAllowed";
  }
}
