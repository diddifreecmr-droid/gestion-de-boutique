/**
 * Champs du formulaire d'article d'après le profil servi. Prêt-à-porter simplifié (décision
 * client du 2026-11-15) : un article = un **nom**, un **SKU facultatif** (la référence) et des
 * prix ; ni taille, ni couleur, ni catégorie, ni type, ni marque. Les autres champs servis
 * restent en base (ils ne sont pas effacés), le formulaire ne les propose plus.
 */
import type { ProfileFieldResponse } from "./catalogAdminContract";

const APPAREL_KEPT = new Set(["name", "reference"]);
const SKU_LABEL = "SKU (référence)";

export function articleFormFields(
  profileCode: string,
  fields: readonly ProfileFieldResponse[],
): ProfileFieldResponse[] {
  if (profileCode !== "apparel") return [...fields];
  const kept = fields.filter((spec) => APPAREL_KEPT.has(spec.code));
  if (!kept.some((spec) => spec.code === "name")) {
    throw new Error("Profil Prêt-à-porter servi sans champ « name »");
  }
  return kept.map((spec) =>
    spec.code === "reference" ? { ...spec, label: SKU_LABEL, required: false } : spec,
  );
}
