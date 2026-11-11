/**
 * Classes partagées par les contrôles (design-system.md § 4.3, § 6.2, § 8), tokens seulement.
 *
 * Le focus des champs et des choix passe par `outline` (et non `ring`) : le `ring` sert déjà
 * à épaissir la bordure à 2 px sans décaler le contenu. Écart de 3 px puis trait de 2 px
 * `primary` : équivalent de `--focus-ring` (0 0 0 3px surface, 0 0 0 5px primary).
 * `outline-solid` est indispensable : `outline-hidden` met `--tw-outline-style` à `none`,
 * que `outline-2` réutiliserait sinon (l'anneau serait invisible).
 */

/** Anneau de focus clavier d'un élément focalisable (bouton, choix, lien). */
export const FOCUS_OUTLINE =
  "outline-hidden focus-visible:outline-2 focus-visible:outline-solid focus-visible:outline-offset-3 " +
  "focus-visible:outline-primary";

/** Cadre d'un champ (§ 6.2) : 48 px, bordure 1 px border-strong ; focus ou erreur = 2 px. */
export function fieldFrameClasses(invalid: boolean): string {
  const state = invalid ? "border-danger ring-1 ring-danger" : "border-border-strong";
  return (
    "flex min-h-(--control-md) w-full items-center gap-2 rounded-md border bg-surface px-4 " +
    `${state} focus-within:border-primary focus-within:ring-1 focus-within:ring-primary ` +
    "focus-within:outline-2 focus-within:outline-solid focus-within:outline-offset-3 " +
    "focus-within:outline-primary"
  );
}

/** Zone de saisie à l'intérieur d'un cadre (le cadre porte la bordure et le focus). */
export const FIELD_INPUT =
  "min-w-0 flex-1 bg-transparent py-3 text-body text-text outline-hidden " +
  "placeholder:text-text-muted";

/** Réaction au toucher (§ 4.5) : seule la couleur change, en --duration-fast. */
export const PRESS_TRANSITION = "transition-colors duration-(--duration-fast) ease-out";

/** Lève une erreur explicite si un texte obligatoire est vide (fail-fast). */
export function requireText(component: string, prop: string, value: string): void {
  if (value.trim() === "") {
    throw new Error(`${component} : ${prop} ne peut pas être vide`);
  }
}
