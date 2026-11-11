/**
 * Version affichée par l'application : `APP_VERSION` si la CI la fournit (ex. étiquette git),
 * sinon `<version de package.json>+<date du build UTC>` (« 0.1.0+20261111.1432 »).
 */
import { readFileSync } from "node:fs";

export function appVersion(env: NodeJS.ProcessEnv = process.env, now: Date = new Date()): string {
  const fromEnv = env["APP_VERSION"]?.trim();
  if (fromEnv !== undefined && fromEnv !== "") return fromEnv;
  const pkg: unknown = JSON.parse(
    readFileSync(new URL("../package.json", import.meta.url), "utf8"),
  );
  const version =
    typeof pkg === "object" && pkg !== null && "version" in pkg ? pkg.version : undefined;
  if (typeof version !== "string" || version === "") {
    throw new Error("package.json : champ « version » absent, version de l'application inconnue");
  }
  const stamp = now.toISOString().replace(/[-:]/g, "").slice(0, 13).replace("T", ".");
  return `${version}+${stamp}`;
}
