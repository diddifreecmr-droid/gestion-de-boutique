/**
 * Erreurs du client HTTP (specs § 6.1, § 6.2). Aucune n'est avalée : le client lève toujours
 * l'une d'elles, l'écran choisit le message.
 */

/** Détails libres de l'enveloppe (`details.until`, `details.field`, `details.fields`…). */
export type ErrorDetails = Readonly<Record<string, unknown>>;

/** Réponse d'erreur de l'API : `{"error": {"code", "message", "details"}}`. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ErrorDetails;

  constructor(status: number, code: string, message: string, details: ErrorDetails = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/** La requête n'a pas atteint le serveur (pas de réseau, DNS, coupure) : « Connexion nécessaire ». */
export class NetworkError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "NetworkError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Lit l'enveloppe d'erreur. Un corps qui ne la respecte pas (proxy, page HTML) donne une
 * `ApiError` au code `HTTP_<statut>` : l'échec reste visible, jamais réinterprété en succès.
 */
export function parseErrorEnvelope(status: number, body: unknown): ApiError {
  const error = isRecord(body) ? body["error"] : undefined;
  if (
    isRecord(error) &&
    typeof error["code"] === "string" &&
    typeof error["message"] === "string"
  ) {
    const details = isRecord(error["details"]) ? error["details"] : {};
    return new ApiError(status, error["code"], error["message"], details);
  }
  return new ApiError(
    status,
    `HTTP_${String(status)}`,
    `Réponse inattendue du serveur (${String(status)})`,
  );
}
