/**
 * Refus `422 PROFILE_CHANGE_BLOCKED` (QC-1, T27) : `details.blocking` est un objet
 * nature → nombre (natures non nulles, dans l'ordre servi). Il devient une phrase française :
 * « 1 article, 1 membre d'un rôle absent du type choisi ». Une nature inconnue ou un nombre
 * invalide est une rupture de contrat (fail-fast) : rien n'est tu.
 */

const NATURES: Readonly<Record<string, readonly [one: string, many: string]>> = {
  articles: ["article", "articles"],
  movements: ["mouvement de stock", "mouvements de stock"],
  sales: ["vente", "ventes"],
  purchases: ["achat", "achats"],
  expenses: ["dépense", "dépenses"],
  receivables: ["créance", "créances"],
  members: ["membre d'un rôle absent du type choisi", "membres d'un rôle absent du type choisi"],
};

function phrase(nature: string, count: unknown): string {
  const words = NATURES[nature];
  if (words === undefined) throw new Error(`Blocage de changement de type inconnu : « ${nature} »`);
  if (typeof count !== "number" || !Number.isInteger(count) || count < 1) {
    throw new Error(`Blocage « ${nature} » : nombre invalide ${JSON.stringify(count)}`);
  }
  return `${String(count)} ${count === 1 ? words[0] : words[1]}`;
}

/** Les blocages, dans l'ordre servi : « 1 article, 1 membre d'un rôle absent du type choisi ». */
export function blockingList(blocking: unknown): string {
  if (typeof blocking !== "object" || blocking === null || Array.isArray(blocking)) {
    throw new Error(`details.blocking attendu (objet), reçu ${JSON.stringify(blocking)}`);
  }
  const entries = Object.entries(blocking);
  if (entries.length === 0) throw new Error("PROFILE_CHANGE_BLOCKED sans aucun blocage");
  return entries.map(([nature, count]) => phrase(nature, count)).join(", ");
}

/** Message de l'écran : ce qui bloque, et ce qu'il reste à faire (recréer la boutique). */
export function blockingText(blocking: unknown): string {
  return (
    `Changement impossible : la boutique a déjà ${blockingList(blocking)}. ` +
    "Seule une boutique sans données change de type ; sinon, ouvrez une boutique du bon type."
  );
}
