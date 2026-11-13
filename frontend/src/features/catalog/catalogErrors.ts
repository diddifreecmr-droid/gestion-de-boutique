/**
 * Messages des refus du catalogue (specs § 6.2, codes de `backend/app/domain/catalog/errors.py`).
 * Seules `ApiError` et `NetworkError` sont traduites ; toute autre erreur est relancée
 * (fail-fast). Un `details` mal formé est une rupture de contrat : on lève.
 */
import { ApiError, NetworkError } from "../../core/api/errors";
import { formatMoney } from "../../shared/format";
import { MODULE_DISABLED, MODULE_DISABLED_MESSAGE } from "../../core/profile/modules";

export const OFFLINE_SAVE =
  "Connexion nécessaire : rien n'a été enregistré. Réessayez quand le réseau revient.";
export const VERSION_CONFLICT_MESSAGE =
  "Cet article a été modifié par quelqu'un d'autre pendant votre saisie. Rechargez-le pour voir la dernière version, puis refaites votre changement.";
export const HAS_STOCK_MESSAGE =
  "Cet article a encore du stock (dans un lieu ou en route) : il ne peut pas être archivé. Vendez ou déplacez d'abord ce stock.";
export const MIN_DISABLED_MESSAGE =
  "Le prix minimum est désactivé dans les réglages de la boutique : laissez-le vide.";
export const FORBIDDEN_MESSAGE = "Vous n'avez pas le droit de faire cette action.";

export type SubmitFailure =
  | { kind: "duplicate"; existingId: string; existingName: string }
  | { kind: "conflict" }
  | { kind: "message"; text: string };

function text(error: ApiError, field: string): string {
  const value = error.details[field];
  if (typeof value !== "string" || value === "") {
    throw new Error(`Détails de l'erreur ${error.code} invalides : « ${field} » absent`);
  }
  return value;
}

function amount(error: ApiError, field: string): number {
  const value = error.details[field];
  if (typeof value !== "number" || !Number.isSafeInteger(value)) {
    throw new Error(`Détails de l'erreur ${error.code} invalides : « ${field} » absent`);
  }
  return value;
}

function apiMessage(error: ApiError): string {
  switch (error.code) {
    case "MIN_PRICE_ABOVE_BASE":
      return `Le prix minimum (${formatMoney(amount(error, "min_price"))}) ne peut pas dépasser le prix de base (${formatMoney(amount(error, "base_price"))}).`;
    case "MIN_PRICE_DISABLED":
      return MIN_DISABLED_MESSAGE;
    case "ARTICLE_HAS_STOCK":
      return HAS_STOCK_MESSAGE;
    case "FORBIDDEN":
      return FORBIDDEN_MESSAGE;
    case MODULE_DISABLED:
      return MODULE_DISABLED_MESSAGE;
    default:
      // Les messages du serveur sont rédigés en français pour l'utilisateur (specs § 6.2).
      return error.message;
  }
}

export function submitFailure(error: unknown): SubmitFailure {
  if (error instanceof NetworkError) return { kind: "message", text: OFFLINE_SAVE };
  if (!(error instanceof ApiError)) throw error;
  if (error.code === "VERSION_CONFLICT") return { kind: "conflict" };
  if (error.code === "DUPLICATE") {
    return {
      kind: "duplicate",
      existingId: text(error, "existing_id"),
      existingName: text(error, "existing_name"),
    };
  }
  return { kind: "message", text: apiMessage(error) };
}

/** Lecture refusée (fiche ou liste) : article introuvable ou droit manquant. */
export function loadFailureMessage(error: ApiError): string {
  if (error.code === "NOT_FOUND") return "Cet article est introuvable.";
  if (error.code === "FORBIDDEN") return FORBIDDEN_MESSAGE;
  if (error.code === MODULE_DISABLED) return MODULE_DISABLED_MESSAGE;
  return error.message;
}
