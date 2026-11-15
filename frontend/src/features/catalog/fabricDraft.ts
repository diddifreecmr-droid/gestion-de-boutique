/**
 * Saisie d'un tissu (Textile, décision du 2026-11-15) : nom, couleurs, prix au mètre et au
 * rouleau, minimums, longueur du rouleau, « au mètre seulement », seuil d'alerte. Le serveur
 * crée un article par couleur (« Djampar — Rouge ») ; ces règles disent tout de suite quoi
 * corriger, le serveur reste juge.
 */
import type {
  ArticleResponse,
  FabricCreateRequest,
  FabricPatchRequest,
} from "../../core/gateways/catalogAdminContract";
import type { CreatePrices } from "./createPrices";
import { thresholdError, thresholdValue } from "./extraValues";

export interface FabricSettings {
  /** Longueur d'un rouleau, en mètres (« 30 », « 25,5 ») ; inutile au mètre seulement. */
  rollLength: string;
  /** Tissu vendu au mètre seulement (ex. Getzner) : ni prix ni longueur de rouleau. */
  meterOnly: boolean;
  threshold: string;
  prices: CreatePrices;
}

export type FabricErrors = Partial<
  Record<"fabric" | "colors" | "rollLength" | "threshold", string>
>;

const LENGTH = /^\d+([.,]\d{1,2})?$/;

/** « Rouge, bleu ; Vert » → ["Rouge", "Bleu", "Vert"] : virgule, point-virgule ou retour. */
export function splitColors(text: string): string[] {
  return text
    .split(/[,;\n]/)
    .map((part) => part.trim().replace(/\s+/g, " "))
    .filter((part) => part !== "")
    .map((part) => part.charAt(0).toLocaleUpperCase("fr") + part.slice(1));
}

/** Ajoute des couleurs sans doublon (casse et accents comparés tels quels, sans espaces). */
export function addColors(current: readonly string[], typed: string): string[] {
  const seen = new Set(current.map((color) => color.toLocaleLowerCase("fr")));
  const next = [...current];
  for (const color of splitColors(typed)) {
    const key = color.toLocaleLowerCase("fr");
    if (!seen.has(key)) {
      seen.add(key);
      next.push(color);
    }
  }
  return next;
}

export function settingsErrors(settings: FabricSettings): FabricErrors {
  const errors: FabricErrors = {};
  const length = settings.rollLength.trim();
  if (!settings.meterOnly && length === "") {
    errors.rollLength = "Indiquez la longueur d'un rouleau (ou « Au mètre seulement »)";
  } else if (
    !settings.meterOnly &&
    (!LENGTH.test(length) || Number(length.replace(",", ".")) <= 0)
  ) {
    errors.rollLength = "Longueur en mètres, par exemple 30 ou 25,5";
  }
  const threshold = thresholdError(settings.threshold);
  if (threshold !== undefined) errors.threshold = threshold;
  return errors;
}

export function createErrors(
  fabric: string,
  colors: readonly string[],
  settings: FabricSettings,
): FabricErrors {
  const errors = settingsErrors(settings);
  if (fabric.trim() === "") errors.fabric = "Indiquez le nom du tissu";
  if (colors.length === 0) errors.colors = "Ajoutez au moins une couleur";
  return errors;
}

const rollLength = (settings: FabricSettings) =>
  settings.meterOnly ? null : settings.rollLength.trim().replace(",", ".");

/** Prix envoyés : le comptable n'en envoie aucun (le serveur refuserait PRICE_SET). */
function pricesOf(settings: FabricSettings, minimum: boolean) {
  const { prices, meterOnly } = settings;
  return {
    base_price: prices.base,
    base_price_piece: meterOnly ? null : prices.piece,
    ...(minimum
      ? { min_price: prices.minimum, min_price_piece: meterOnly ? null : prices.minimumPiece }
      : {}),
  };
}

export interface PriceRights {
  /** Le rôle fixe les prix (propriétaire). */
  setPrices: boolean;
  /** Réglage « prix minimum » de la boutique. */
  minPriceEnabled: boolean;
}

export function createBody(
  fabric: string,
  colors: readonly string[],
  settings: FabricSettings,
  rights: PriceRights,
): FabricCreateRequest {
  return {
    fabric: fabric.trim(),
    colors: [...colors],
    roll_length_m: rollLength(settings),
    meter_only: settings.meterOnly,
    alert_threshold: thresholdValue(settings.threshold),
    ...(rights.setPrices ? pricesOf(settings, rights.minPriceEnabled) : {}),
  };
}

const decimalText = (value: string | null) =>
  value === null
    ? ""
    : value
        .replace(/\.0+$/, "")
        .replace(/(\.\d*?)0+$/, "$1")
        .replace(".", ",");

/** Réglages actuels d'un tissu, lus sur une de ses couleurs (elles les partagent). */
export function settingsOf(color: ArticleResponse): FabricSettings {
  return {
    rollLength: decimalText(color.piece_length_m),
    meterOnly: !color.sold_by_piece,
    threshold: decimalText(color.alert_threshold),
    prices: {
      base: color.base_price ?? null,
      minimum: color.min_price ?? null,
      piece: color.base_price_piece ?? null,
      minimumPiece: color.min_price_piece ?? null,
    },
  };
}

/** Changement du tissu : tous les champs repartent (le serveur l'applique à chaque couleur). */
export function patchBody(settings: FabricSettings, rights: PriceRights): FabricPatchRequest {
  return {
    roll_length_m: rollLength(settings),
    meter_only: settings.meterOnly,
    alert_threshold: thresholdValue(settings.threshold),
    ...(rights.setPrices ? { prices: pricesOf(settings, rights.minPriceEnabled) } : {}),
  };
}
