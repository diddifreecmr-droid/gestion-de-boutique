/**
 * Paramètres de chemin et de requête des routes du contrat (`/shops/{shop_id}/articles`).
 * Un paramètre manquant, vide ou en trop est une erreur de câblage : on lève (fail-fast).
 */

/** Valeurs de `?clé=valeur` ; `null` / `undefined` = paramètre omis. */
export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Readonly<Record<string, QueryValue>>;
export type PathParams = Readonly<Record<string, string>>;

/** Remplace chaque `{nom}` par sa valeur encodée. */
export function fillPath(path: string, params: PathParams = {}): string {
  const used = new Set<string>();
  const filled = path.replace(/\{([a-z_]+)\}/g, (_match, name: string) => {
    const value = params[name];
    if (value === undefined || value === "") {
      throw new Error(`Paramètre de chemin « ${name} » absent pour « ${path} »`);
    }
    used.add(name);
    return encodeURIComponent(value);
  });
  const extra = Object.keys(params).filter((name) => !used.has(name));
  if (extra.length > 0) {
    throw new Error(`Paramètres inconnus pour « ${path} » : ${extra.join(", ")}`);
  }
  return filled;
}

/** `?q=hao&status=all` (paramètres omis si `null`/`undefined`), ou `""`. */
export function queryString(query: QueryParams = {}): string {
  const search = new URLSearchParams();
  for (const [name, value] of Object.entries(query)) {
    if (value !== null && value !== undefined) search.append(name, String(value));
  }
  const text = search.toString();
  return text === "" ? "" : `?${text}`;
}
