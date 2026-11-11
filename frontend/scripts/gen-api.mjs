/**
 * Types TypeScript du contrat de l'API, générés depuis `backend/openapi.json` (specs § 6.1).
 * Le contrat est exporté par le backend (`python -m tools.export_openapi`) ; ce fichier n'est
 * jamais écrit à la main.
 *
 * Usage : node scripts/gen-api.mjs           écrit src/core/api/schema.gen.ts
 *         node scripts/gen-api.mjs --check   échoue si le fichier n'est plus à jour
 */
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";
import { format, resolveConfig } from "prettier";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const CONTRACT = resolve(ROOT, "../backend/openapi.json");
export const OUTPUT = resolve(ROOT, "src/core/api/schema.gen.ts");

const HEADER =
  "/* Fichier GÉNÉRÉ par `npm run gen:api` depuis backend/openapi.json : ne pas modifier. */\n";

/** Contenu attendu de schema.gen.ts (formaté par Prettier comme le reste du code). */
export async function generateSchema(contract = CONTRACT) {
  if (!existsSync(contract)) {
    throw new Error(`Contrat introuvable : ${contract} (lancez python -m tools.export_openapi)`);
  }
  const ast = await openapiTS(pathToFileURL(contract));
  const source = HEADER + astToString(ast);
  const options = (await resolveConfig(OUTPUT)) ?? {};
  return format(source, { ...options, filepath: OUTPUT });
}

/** `true` si le fichier versionné est identique à ce que produit le contrat actuel. */
export async function isUpToDate(contract = CONTRACT, output = OUTPUT) {
  if (!existsSync(output)) return false;
  return readFileSync(output, "utf8") === (await generateSchema(contract));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const shown = relative(process.cwd(), OUTPUT);
  if (process.argv.includes("--check")) {
    if (!(await isUpToDate())) {
      console.error(`check:api — ${shown} n'est plus à jour : lancez npm run gen:api.`);
      process.exit(1);
    }
    console.log(`check:api — OK, ${shown} correspond à backend/openapi.json.`);
  } else {
    writeFileSync(OUTPUT, await generateSchema());
    console.log(`gen:api — ${shown} généré depuis backend/openapi.json.`);
  }
}
