/**
 * Échoue si un fichier .ts/.tsx dépasse MAX_LINES lignes (CLAUDE.md : modularité).
 * Usage : node scripts/check-length.mjs [dossier…]   (par défaut : src)
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

export const MAX_LINES = 200;

export function countLines(text) {
  if (text === "") return 0;
  const lines = text.split(/\r?\n/);
  return lines.at(-1) === "" ? lines.length - 1 : lines.length;
}

export function* sourceFiles(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* sourceFiles(path);
    else if (/\.tsx?$/.test(entry.name)) yield path;
  }
}

export function findTooLong(dirs, max = MAX_LINES) {
  const offenders = [];
  for (const dir of dirs) {
    for (const file of sourceFiles(dir)) {
      const lines = countLines(readFileSync(file, "utf8"));
      if (lines > max) offenders.push({ file, lines });
    }
  }
  return offenders;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const dirs = process.argv.length > 2 ? process.argv.slice(2) : ["src"];
  const offenders = findTooLong(dirs);
  for (const { file, lines } of offenders) {
    console.error(`${relative(process.cwd(), file)} : ${lines} lignes (max ${MAX_LINES})`);
  }
  if (offenders.length > 0) {
    console.error(`check:length — ${offenders.length} fichier(s) trop long(s).`);
    process.exit(1);
  }
  console.log(
    `check:length — OK, aucun fichier .ts/.tsx de ${dirs.join(", ")} au-delà de ${MAX_LINES} lignes.`,
  );
}
