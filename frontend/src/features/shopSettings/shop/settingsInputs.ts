/**
 * Lecture des saisies numériques des réglages (bornes du backend `domain/shops/settings.py`).
 * Résultat : la valeur à envoyer, ou un message d'erreur à afficher sous le champ.
 */
import type { SettingsPatch, ShopSettings } from "../../../core/gateways/shopAdminContract";

export type Parsed<T> = { ok: true; value: T } | { ok: false; error: string };

/** Seuil de stock bas : décimal ≥ 0 au dixième près, virgule acceptée (« 2,5 »). */
export function parseThreshold(text: string): Parsed<string> {
  const cleaned = text.trim().replace(",", ".");
  if (!/^\d{1,6}(\.\d)?$/.test(cleaned)) {
    return { ok: false, error: "Un nombre positif, au dixième près (ex. 2 ou 2,5)" };
  }
  return { ok: true, value: cleaned };
}

/** Entier facultatif borné : vide → null (réglage effacé). */
export function parseOptionalInt(text: string, low: number, high: number): Parsed<number | null> {
  const cleaned = text.trim();
  if (cleaned === "") return { ok: true, value: null };
  const value = /^\d{1,4}$/.test(cleaned) ? Number(cleaned) : Number.NaN;
  if (Number.isNaN(value) || value < low || value > high) {
    return { ok: false, error: `Un nombre entier de ${String(low)} à ${String(high)}, ou vide` };
  }
  return { ok: true, value };
}

/** Texte facultatif : vide → null. */
export function optionalText(text: string): string | null {
  const cleaned = text.trim();
  return cleaned === "" ? null : cleaned;
}

/** Ne garde que les champs qui changent par rapport aux réglages lus. */
export function changesOf(
  settings: ShopSettings,
  wanted: Omit<SettingsPatch, "version">,
): Omit<SettingsPatch, "version"> {
  const header: Readonly<Record<string, unknown>> = settings.header;
  const current: Readonly<Record<string, unknown>> = { ...settings, ...header };
  return Object.fromEntries(
    Object.entries(wanted).filter(([name, value]) => current[name] !== value),
  );
}
