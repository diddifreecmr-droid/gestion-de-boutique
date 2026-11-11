/**
 * Lecture typée des `details` des erreurs métier d'une vente (specs § 6.2). Un détail mal
 * formé est une rupture de contrat : on lève une erreur explicite (fail-fast).
 */
import type { ApiError, ErrorDetails } from "../api/errors";

export interface OtherLocationStock {
  /** HYPOTHÈSE : specs § 6.2 dit `other_locations[]` sans en donner la forme. */
  location_id: string;
  location_name: string;
  available: string;
}

export interface StockInsufficientDetails {
  /** HYPOTHÈSE : l'article en cause (nécessaire quand la vente a plusieurs lignes). */
  article_id: string;
  available: string;
  other_locations: OtherLocationStock[];
}

export interface PriceBelowMinimumDetails {
  /** HYPOTHÈSE : l'article en cause. */
  article_id: string;
  min_price: number;
  request_required: boolean;
}

export interface DuplicateDetails {
  field: string;
  value: string;
  /** HYPOTHÈSE : la vente qui porte déjà ce châssis (RG-M01 « montre la vente concernée »). */
  sale_number: string | null;
}

function fail(code: string, field: string): never {
  throw new Error(`Détails de l'erreur ${code} invalides : « ${field} » absent ou mal formé`);
}

function text(details: ErrorDetails, code: string, field: string): string {
  const value = details[field];
  return typeof value === "string" ? value : fail(code, field);
}

function integer(details: ErrorDetails, code: string, field: string): number {
  const value = details[field];
  return Number.isSafeInteger(value) ? (value as number) : fail(code, field);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function stockInsufficient(error: ApiError): StockInsufficientDetails {
  const code = "STOCK_INSUFFICIENT";
  const raw = error.details["other_locations"];
  if (!Array.isArray(raw)) fail(code, "other_locations");
  const others = raw.map((entry: unknown) => {
    if (!isRecord(entry)) fail(code, "other_locations");
    return {
      location_id: text(entry, code, "location_id"),
      location_name: text(entry, code, "location_name"),
      available: text(entry, code, "available"),
    };
  });
  return {
    article_id: text(error.details, code, "article_id"),
    available: text(error.details, code, "available"),
    other_locations: others,
  };
}

export function priceBelowMinimum(error: ApiError): PriceBelowMinimumDetails {
  const code = "PRICE_BELOW_MINIMUM";
  const required = error.details["request_required"];
  if (typeof required !== "boolean") fail(code, "request_required");
  return {
    article_id: text(error.details, code, "article_id"),
    min_price: integer(error.details, code, "min_price"),
    request_required: required,
  };
}

export function duplicate(error: ApiError): DuplicateDetails {
  const code = "DUPLICATE";
  const sale = error.details["sale_number"];
  return {
    field: text(error.details, code, "field"),
    value: text(error.details, code, "value"),
    sale_number: typeof sale === "string" ? sale : null,
  };
}
