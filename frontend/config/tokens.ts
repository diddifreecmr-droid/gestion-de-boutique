import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/** Chemin unique des tokens (design-system.md § 9.1). */
export const TOKENS_CSS = fileURLToPath(new URL("../src/shared/ui/tokens.css", import.meta.url));

/**
 * Lit la valeur d'un token dans le CSS donné. Utilisé par la configuration de build
 * (manifest, theme-color, icônes) pour ne jamais recopier une couleur hors de tokens.css.
 * Échoue si le token est absent ou défini deux fois.
 */
export function readToken(css: string, name: string): string {
  if (!/^--[a-z0-9-]+$/.test(name)) {
    throw new Error(`Nom de token invalide : « ${name} »`);
  }
  const pattern = new RegExp(`^\\s*${name}\\s*:\\s*([^;]+);`, "gm");
  const matches = [...css.matchAll(pattern)];
  const [first] = matches;
  if (first === undefined || matches.length !== 1) {
    throw new Error(
      `Token ${name} : ${String(matches.length)} définition(s) trouvée(s), 1 attendue`,
    );
  }
  const value = first[1]?.trim();
  if (value === undefined || value === "") {
    throw new Error(`Token ${name} vide`);
  }
  return value;
}

export function readTokenFromFile(name: string, file: string = TOKENS_CSS): string {
  return readToken(readFileSync(file, "utf8"), name);
}
