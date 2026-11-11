// @vitest-environment node
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { generateSchema, isUpToDate, OUTPUT } from "../../scripts/gen-api.mjs";

let dir = "";
afterEach(() => {
  if (dir !== "") rmSync(dir, { recursive: true, force: true });
});

describe("gen-api (équivalent de npm run check:api)", () => {
  it("le client versionné correspond au contrat backend/openapi.json", async () => {
    expect(await isUpToDate()).toBe(true);
  });

  it("signale un client périmé ou absent", async () => {
    dir = mkdtempSync(join(tmpdir(), "gen-api-"));
    const stale = join(dir, "schema.gen.ts");
    writeFileSync(stale, "export interface paths {}\n");
    expect(await isUpToDate(undefined, stale)).toBe(false);
    expect(await isUpToDate(undefined, join(dir, "absent.gen.ts"))).toBe(false);
  });

  it("génère les routes d'authentification avec l'en-tête « ne pas modifier »", async () => {
    const source = await generateSchema();
    expect(source).toMatch(/^\/\* Fichier GÉNÉRÉ par `npm run gen:api`/);
    expect(source).toContain('"/api/v1/auth/login"');
    expect(OUTPUT).toMatch(/schema\.gen\.ts$/);
  });

  it("échoue explicitement si le contrat est introuvable", async () => {
    await expect(generateSchema(join(tmpdir(), "absent-openapi.json"))).rejects.toThrow(
      "Contrat introuvable",
    );
  });
});
