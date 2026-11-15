/**
 * Regroupement par tissu (Textile, 2026-11-15) : chaque couleur est un article (« Djampar —
 * Rouge ») portant `fabric` ; la liste les range sous leur tissu, dans l'ordre du serveur. Un
 * article sans tissu reste seul (`fabric: null`).
 */

export interface FabricGroup<T> {
  /** Nom du tissu, ou `null` pour les articles sans tissu. */
  fabric: string | null;
  items: T[];
}

/** Groupes dans l'ordre de première apparition ; les articles sans tissu, chacun à son rang. */
export function groupByFabric<T extends { fabric: string | null }>(
  items: readonly T[],
): FabricGroup<T>[] {
  const groups: FabricGroup<T>[] = [];
  const byFabric = new Map<string, FabricGroup<T>>();
  for (const item of items) {
    const fabric = item.fabric?.trim() ?? "";
    if (fabric === "") {
      groups.push({ fabric: null, items: [item] });
      continue;
    }
    const known = byFabric.get(fabric);
    if (known !== undefined) {
      known.items.push(item);
      continue;
    }
    const group = { fabric, items: [item] };
    byFabric.set(fabric, group);
    groups.push(group);
  }
  return groups;
}

const SEPARATOR = " — ";

/** Couleur d'un article de tissu : l'attribut `color`, sinon la fin de « Tissu — Couleur ». */
export function colorOf(article: {
  display_name: string;
  attributes: Readonly<Record<string, unknown>>;
}): string {
  const color = article.attributes["color"];
  if (typeof color === "string" && color.trim() !== "") return color.trim();
  const at = article.display_name.lastIndexOf(SEPARATOR);
  if (at < 0) throw new Error(`« ${article.display_name} » : couleur introuvable`);
  return article.display_name.slice(at + SEPARATOR.length).trim();
}
