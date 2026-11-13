/**
 * Titre d'un article à l'écran de vente : le nom sans mot répété (audit UX du 13/11/2026,
 * « Robe Bleu Marine Robe » = nom + type recollés). Le nom enregistré n'est pas modifié ;
 * le reçu, document officiel, garde le nom tel que le serveur l'a figé.
 */

/** Forme de comparaison : sans accents ni casse (« Robe » = « robe »). */
function fold(word: string): string {
  return word
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase("fr");
}

/** Taille de la plus longue fin qui recopie le début (« Robe … Robe » → 1), sinon 0. */
function tailCopyingHead(words: readonly string[]): number {
  for (let size = Math.floor(words.length / 2); size >= 1; size -= 1) {
    const head = words.slice(0, size).join(" ");
    if (words.slice(words.length - size).join(" ") === head) return size;
  }
  return 0;
}

/**
 * Retire les mots collés deux fois de suite (« Robe Robe ») et une fin qui recopie le début
 * du nom (« Robe Bleu Marine Robe » → « Robe Bleu Marine »). Un mot répété ailleurs reste
 * (« Tissu Wax Super Wax »). Un nom vide est une erreur.
 */
export function articleTitle(name: string): string {
  const raw = name.trim().split(/\s+/u);
  if (raw[0] === undefined || raw[0] === "") throw new Error("Article sans nom à afficher");
  const kept: string[] = [];
  for (const word of raw) {
    const last = kept[kept.length - 1];
    if (last === undefined || fold(last) !== fold(word)) kept.push(word);
  }
  const size = tailCopyingHead(kept.map(fold));
  return kept.slice(0, kept.length - size).join(" ");
}
