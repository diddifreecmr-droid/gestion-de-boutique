/**
 * Messages des refus du stock (specs § 6.2, `backend/app/domain/stock/errors.py`). Seules
 * `ApiError` et `NetworkError` sont traduites ; toute autre erreur est relancée (fail-fast).
 * Un `details` mal formé est une rupture de contrat : on lève.
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { formatQuantity } from "../../shared/format";

export const OFFLINE_SAVE =
  "Connexion nécessaire : rien n'a été enregistré. Réessayez quand le réseau revient.";
export const FORBIDDEN_MESSAGE = "Vous n'avez pas le droit de faire cette action.";
export const INVENTORY_CONFLICT =
  "Cet inventaire a été modifié sur un autre appareil pendant votre saisie. Rechargez-le pour voir les dernières quantités.";

export type StockFailure =
  | { kind: "message"; text: string }
  | { kind: "conflict" }
  /** Un inventaire est déjà en cours dans ce lieu : on propose de le reprendre. */
  | { kind: "inventoryOpen"; inventoryId: string | null }
  /** Écarts sans motif (validation d'inventaire) : articles concernés, sans le théorique. */
  | { kind: "reasons"; articleIds: readonly string[] };

function detail(error: ApiError, field: string): unknown {
  if (!(field in error.details)) {
    throw new Error(`Détails de l'erreur ${error.code} invalides : « ${field} » absent`);
  }
  return error.details[field];
}

function text(error: ApiError, field: string): string {
  const value = detail(error, field);
  if (typeof value !== "string" || value === "") {
    throw new Error(
      `Détails de l'erreur ${error.code} invalides : « ${field} » n'est pas un texte`,
    );
  }
  return value;
}

function others(error: ApiError): string {
  const value = detail(error, "other_locations");
  if (!Array.isArray(value)) throw new Error("STOCK_INSUFFICIENT : other_locations invalide");
  const parts = value.map((entry: unknown) => {
    if (typeof entry !== "object" || entry === null) {
      throw new Error("STOCK_INSUFFICIENT : lieu invalide dans other_locations");
    }
    const { location_name: name, available } = entry as Record<string, unknown>;
    if (typeof name !== "string" || typeof available !== "string") {
      throw new Error("STOCK_INSUFFICIENT : lieu invalide dans other_locations");
    }
    return `${name} : ${formatQuantity(available)}`;
  });
  return parts.length === 0 ? "" : ` Autres lieux — ${parts.join(", ")}.`;
}

/** « Stock insuffisant : 1 disponible à Garoua. Autres lieux — Ngaoundéré : 3. » */
export function insufficientMessage(error: ApiError, locationName: string): string {
  const available = formatQuantity(text(error, "available"));
  return `Stock insuffisant : ${available} disponible à ${locationName}.${others(error)}`;
}

function articleList(error: ApiError): readonly string[] {
  const value = detail(error, "articles");
  if (!Array.isArray(value) || !value.every((id): id is string => typeof id === "string")) {
    throw new Error("VALIDATION_ERROR : liste « articles » invalide");
  }
  return value;
}

/**
 * Traduit un refus d'envoi. `locationName` : lieu de l'ajustement (message de stock
 * insuffisant). Toute erreur hors API et réseau est relancée.
 */
export function stockFailure(error: unknown, locationName = ""): StockFailure {
  if (error instanceof NetworkError) return { kind: "message", text: OFFLINE_SAVE };
  if (!(error instanceof ApiError)) throw error;
  switch (error.code) {
    case "VERSION_CONFLICT":
      return { kind: "conflict" };
    case "INVENTORY_IN_PROGRESS": {
      const id = detail(error, "inventory_id");
      if (id !== null && typeof id !== "string") throw new Error("inventory_id invalide");
      return { kind: "inventoryOpen", inventoryId: id };
    }
    case "STOCK_INSUFFICIENT":
      return { kind: "message", text: insufficientMessage(error, locationName) };
    case "FORBIDDEN":
      return { kind: "message", text: FORBIDDEN_MESSAGE };
    case "VALIDATION_ERROR":
      if (error.details["field"] === "reasons") {
        return { kind: "reasons", articleIds: articleList(error) };
      }
      return { kind: "message", text: error.message };
    default:
      // Les messages du serveur sont rédigés en français pour l'utilisateur (specs § 6.2).
      return { kind: "message", text: error.message };
  }
}

/** Lecture refusée : introuvable ou droit manquant. */
export function loadFailureMessage(error: ApiError): string {
  if (error.code === "NOT_FOUND") return "Élément introuvable dans cette boutique.";
  if (error.code === "FORBIDDEN") return FORBIDDEN_MESSAGE;
  return error.message;
}

/** Texte d'un refus, quel que soit son genre (écrans sans traitement particulier). */
export function failureText(failure: StockFailure): string {
  switch (failure.kind) {
    case "message":
      return failure.text;
    case "conflict":
      return INVENTORY_CONFLICT;
    case "inventoryOpen":
      return "Un inventaire est déjà en cours dans ce lieu.";
    case "reasons":
      return "Un motif est obligatoire pour chaque écart (ou un motif global).";
  }
}
