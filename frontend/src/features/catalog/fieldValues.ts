/**
 * Champs d'article **décrits par le profil** (`GET /profile` → `article_fields`, specs § 4.5) :
 * saisie en texte, conversion vers les valeurs de l'API, contrôles avant envoi (le serveur
 * reste juge). Un type de champ inconnu est une rupture de contrat (fail-fast).
 */
import type { FieldValue, ProfileFieldResponse } from "../../core/gateways/catalogAdminContract";

export type FieldKind = "text" | "integer" | "decimal" | "boolean" | "choice";

/** Saisie du formulaire, par code de champ (texte brut ; `"true"`/`"false"` pour Oui/Non). */
export type FieldDraft = Readonly<Record<string, string>>;
export type FieldErrors = Readonly<Record<string, string>>;

const KINDS: readonly FieldKind[] = ["text", "integer", "decimal", "boolean", "choice"];
const INTEGER = /^\d+$/;
const DECIMAL = /^\d+([.,]\d{1,2})?$/;

export function fieldKind(spec: ProfileFieldResponse): FieldKind {
  const kind = KINDS.find((known) => known === spec.kind);
  if (kind === undefined) {
    throw new Error(`Type de champ inconnu « ${spec.kind} » (champ « ${spec.code} »)`);
  }
  return kind;
}

/** Valeur lue de l'article → texte du champ. */
export function draftOf(
  fields: readonly ProfileFieldResponse[],
  values: Readonly<Record<string, FieldValue>>,
): FieldDraft {
  const draft: Record<string, string> = {};
  for (const spec of fields) {
    const value = values[spec.code];
    draft[spec.code] = value === null || value === undefined ? "" : String(value);
  }
  return draft;
}

export function emptyDraft(fields: readonly ProfileFieldResponse[]): FieldDraft {
  return draftOf(fields, {});
}

function convert(spec: ProfileFieldResponse, text: string): FieldValue {
  const value = text.trim();
  if (value === "") return null;
  switch (fieldKind(spec)) {
    case "integer":
      return Number(value);
    case "decimal":
      return value.replace(",", ".");
    case "boolean":
      return value === "true";
    case "text":
    case "choice":
      return value;
  }
}

function problem(spec: ProfileFieldResponse, text: string): string | null {
  const value = text.trim();
  if (value === "") return spec.required ? `${spec.label} : champ obligatoire` : null;
  const kind = fieldKind(spec);
  if (kind === "integer" && (!INTEGER.test(value) || Number(value) < 1)) {
    return `${spec.label} : nombre entier attendu (ex. 125)`;
  }
  if (kind === "decimal" && !DECIMAL.test(value)) {
    return `${spec.label} : nombre attendu (ex. 2,5)`;
  }
  if (kind === "choice" && !spec.choices.includes(value)) return `${spec.label} : choix inconnu`;
  return null;
}

export function checkDraft(
  fields: readonly ProfileFieldResponse[],
  draft: FieldDraft,
): FieldErrors {
  const errors: Record<string, string> = {};
  for (const spec of fields) {
    const message = problem(spec, draft[spec.code] ?? "");
    if (message !== null) errors[spec.code] = message;
  }
  return errors;
}

/** Tous les champs renseignés (création). */
export function fieldValues(
  fields: readonly ProfileFieldResponse[],
  draft: FieldDraft,
): Record<string, FieldValue> {
  const values: Record<string, FieldValue> = {};
  for (const spec of fields) {
    const value = convert(spec, draft[spec.code] ?? "");
    if (value !== null) values[spec.code] = value;
  }
  return values;
}

/** Seulement les champs changés (modification) ; un champ vidé part à `null` (effacé). */
export function changedValues(
  fields: readonly ProfileFieldResponse[],
  before: FieldDraft,
  after: FieldDraft,
): Record<string, FieldValue> {
  const changed: Record<string, FieldValue> = {};
  for (const spec of fields) {
    const next = (after[spec.code] ?? "").trim();
    if (next !== (before[spec.code] ?? "").trim()) changed[spec.code] = convert(spec, next);
  }
  return changed;
}
