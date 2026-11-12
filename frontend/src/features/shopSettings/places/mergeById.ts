/**
 * Liste lue au chargement, mise à jour par les réponses des envois (créés ou modifiés), triée
 * par ordre d'affichage puis par nom : l'écran n'a pas à relire toute la liste.
 */
export function mergeById<T extends { id: string; display_order: number; name: string }>(
  initial: readonly T[],
  changed: readonly T[],
): T[] {
  const byId = new Map(initial.map((item) => [item.id, item]));
  for (const item of changed) byId.set(item.id, item);
  return [...byId.values()].sort(
    (a, b) => a.display_order - b.display_order || a.name.localeCompare(b.name, "fr"),
  );
}
