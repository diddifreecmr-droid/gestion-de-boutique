/**
 * Prouve que la vitrine `/_ui` (développement uniquement) est absente du build de
 * production : aucun fichier de dist/ ne doit contenir ses marqueurs. Lancer après `build`.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

/** Chaînes propres à la vitrine (route, titre, composants internes). */
const MARKERS = ["/_ui", "Vitrine des composants", "UiShowcase", "TokenPalette", "ButtonGallery"];
const DIST = "dist";

function* files(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) yield* files(path);
    else yield path;
  }
}

let checked = 0;
const hits = [];
for (const file of files(DIST)) {
  if (!/\.(js|css|html|webmanifest|json)$/.test(file)) continue;
  checked++;
  const text = readFileSync(file, "utf8");
  for (const marker of MARKERS)
    if (text.includes(marker)) hits.push(`${file} contient « ${marker} »`);
}
if (checked === 0)
  throw new Error("dist/ ne contient aucun fichier à inspecter : lancez d'abord npm run build");
if (hits.length > 0) {
  console.error(hits.join("\n"));
  process.exit(1);
}
console.log(
  `check:no-showcase — OK, ${checked} fichiers de dist/ inspectés, aucune trace de /_ui.`,
);
