/**
 * Initiales du logo générique : première lettre (ou chiffre) des deux premiers mots du nom,
 * en capitales (« Motos Garoua » → « MG », « Textile » → « T »). Un nom sans lettre ni chiffre
 * est une rupture de contrat (le nom d'une boutique est toujours écrit).
 */
export function initialsOf(name: string): string {
  const words = name.match(/[\p{L}\p{N}][\p{L}\p{N}\p{M}'’]*/gu) ?? [];
  const letters = words.slice(0, 2).map((word) => Array.from(word)[0] ?? "");
  const initials = letters.join("").toLocaleUpperCase("fr");
  if (initials === "") throw new Error(`Nom de boutique sans lettre : « ${name} »`);
  return initials;
}
