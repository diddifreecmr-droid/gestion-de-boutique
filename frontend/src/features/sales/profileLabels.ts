/**
 * Libellés de recherche selon le profil de la boutique (audit UX du 13/11/2026) : on ne parle
 * de « modèle » ou de « châssis » que si le profil a ces champs (`GET /profile`).
 */
import type { ProfileFieldLabel } from "../../core/gateways/catalogContract";

/** Champs que la recherche d'article du serveur compare (nom affiché, marque, modèle, référence). */
const SEARCHABLE = new Set(["name", "brand", "model", "reference"]);

/** Libellé par défaut quand le profil ne nomme aucun champ cherchable. */
export const DEFAULT_ARTICLE_SEARCH = "nom ou référence";

/** « a », « a ou b », « a, b ou c ». */
function joinOr(words: readonly string[]): string {
  if (words.length < 2) return words.join("");
  return `${words.slice(0, -1).join(", ")} ou ${words[words.length - 1] ?? ""}`;
}

/** Aide du champ « Article » : « Cherchez par marque ou modèle » (Motos), « … nom ou référence ». */
export function articleSearchHint(fields: readonly ProfileFieldLabel[]): string {
  const labels = fields
    .filter((field) => SEARCHABLE.has(field.code))
    .map((field) => {
      if (field.label.trim() === "") throw new Error(`Champ « ${field.code} » sans libellé`);
      return field.label.trim().toLocaleLowerCase("fr");
    });
  return `Cherchez par ${labels.length === 0 ? DEFAULT_ARTICLE_SEARCH : joinOr(labels)}`;
}

/** Le profil saisit-il un n° de châssis à la vente (la recherche des ventes le trouve) ? */
export function searchesChassis(saleFields: readonly string[]): boolean {
  return saleFields.includes("chassis_number");
}

/** Libellé de la recherche de la liste des ventes. */
export function saleSearchLabel(chassis: boolean): string {
  return chassis ? "Chercher un n° de vente ou de châssis" : "Chercher un n° de vente";
}
