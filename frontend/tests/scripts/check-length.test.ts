// @vitest-environment node
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { countLines, findTooLong, MAX_LINES } from "../../scripts/check-length.mjs";

let dir = "";
afterEach(() => {
  if (dir !== "") rmSync(dir, { recursive: true, force: true });
});

describe("check-length", () => {
  it("compte les lignes (fin de ligne finale ignorée, CRLF accepté)", () => {
    expect(countLines("")).toBe(0);
    expect(countLines("a\nb\n")).toBe(2);
    expect(countLines("a\r\nb")).toBe(2);
  });

  it(`signale seulement les fichiers .ts/.tsx de plus de ${String(MAX_LINES)} lignes`, () => {
    dir = mkdtempSync(join(tmpdir(), "check-length-"));
    mkdirSync(join(dir, "sub"));
    writeFileSync(join(dir, "ok.ts"), "x\n".repeat(MAX_LINES));
    writeFileSync(join(dir, "sub", "long.tsx"), "x\n".repeat(MAX_LINES + 1));
    writeFileSync(join(dir, "long.css"), "x\n".repeat(MAX_LINES + 50));
    const offenders = findTooLong([dir]);
    expect(offenders).toEqual([{ file: join(dir, "sub", "long.tsx"), lines: MAX_LINES + 1 }]);
  });
});
