/** Largeur des barres de la répartition par catégorie (UC-DEP-03). */

/**
 * Largeurs des barres, par pas de 5 % : écrites en entier pour que Tailwind les génère
 * (aucune valeur arbitraire ni `style=`, design-system § 9.2).
 */
const WIDTHS = [
  "w-0",
  "w-1/20",
  "w-2/20",
  "w-3/20",
  "w-4/20",
  "w-5/20",
  "w-6/20",
  "w-7/20",
  "w-8/20",
  "w-9/20",
  "w-10/20",
  "w-11/20",
  "w-12/20",
  "w-13/20",
  "w-14/20",
  "w-15/20",
  "w-16/20",
  "w-17/20",
  "w-18/20",
  "w-19/20",
  "w-full",
] as const;

/** Classe de largeur d'une part ; une part non nulle se voit toujours (au moins 5 %). */
export function barWidth(amount: number, total: number): string {
  if (amount < 0 || total <= 0 || amount > total) {
    throw new Error(`barWidth : part ${String(amount)} incohérente avec ${String(total)}`);
  }
  const steps = Math.max(amount > 0 ? 1 : 0, Math.round((amount / total) * 20));
  const width = WIDTHS[steps];
  if (width === undefined) throw new Error(`barWidth : pas ${String(steps)} hors échelle`);
  return width;
}
