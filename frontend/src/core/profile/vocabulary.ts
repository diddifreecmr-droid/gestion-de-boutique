/**
 * Vocabulaire qui dépend du type de boutique (T39, audit UX du 13/11/2026) : les écrans ne
 * parlent de « marque », « modèle » ou « châssis » que si le profil servi a ces champs, et
 * nomment les rôles avec les libellés du profil (« Vendeur » en Motos, « Employé » ailleurs).
 */

/** Champ décrit par le profil (code et libellé suffisent ici). */
export interface FieldLabel {
  code: string;
  label: string;
}

/** Champs que la recherche d'article du serveur compare (nom affiché, marque, modèle, référence). */
const SEARCHABLE = new Set(["name", "brand", "model", "reference"]);

/** Libellés (en minuscules) des champs cherchables du profil, dans l'ordre du profil. */
export function searchableLabels(fields: readonly FieldLabel[]): string[] {
  return fields
    .filter((field) => SEARCHABLE.has(field.code))
    .map((field) => {
      if (field.label.trim() === "") throw new Error(`Champ « ${field.code} » sans libellé`);
      return field.label.trim().toLocaleLowerCase("fr");
    });
}

/** « a », « a ou b », « a, b ou c ». */
export function joinOr(words: readonly string[]): string {
  if (words.length < 2) return words.join("");
  return `${words.slice(0, -1).join(", ")} ou ${words[words.length - 1] ?? ""}`;
}

/** Aide d'une recherche d'article en liste : « Nom, marque ou référence » (Prêt-à-porter). */
export function listSearchHint(fields: readonly FieldLabel[]): string {
  const labels = searchableLabels(fields);
  const text = joinOr(labels.length === 0 ? ["nom", "référence"] : labels);
  return text.charAt(0).toLocaleUpperCase("fr") + text.slice(1);
}

/** « Vendeurs » ou « Employés » : pluriel du libellé d'un rôle servi par le profil. */
export function rolePlural(label: string): string {
  if (label.trim() === "") throw new Error("Libellé de rôle vide");
  return /[sxz]$/i.test(label) ? label : `${label}s`;
}

/** Libellé servi d'un rôle, en minuscules dans une phrase : « les employés ». */
export function roleWord(label: string, plural = false): string {
  return (plural ? rolePlural(label) : label).toLocaleLowerCase("fr");
}
