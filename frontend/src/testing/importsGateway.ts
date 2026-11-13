/**
 * Fausse passerelle d'import pour les tests d'écran : chaque méthode est un `vi.fn` qui
 * répond par les données typées de `testing/imports`. Réservé aux tests.
 */
import { vi, type Mock } from "vitest";
import type { ImportsGateway } from "../core/gateways/importsContract";
import { importBatch, importBatchDetail, importPreview } from "./imports";

export type ImportsMocks = { [K in keyof ImportsGateway]: Mock<ImportsGateway[K]> };

export function fakeImportsGateway(overrides: Partial<ImportsMocks> = {}): ImportsMocks {
  return {
    template: vi.fn(() => Promise.resolve({ blob: new Blob(["x"]), fileName: "modele.xlsx" })),
    preview: vi.fn(() => Promise.resolve(importPreview())),
    confirm: vi.fn(() => Promise.resolve(importBatch())),
    list: vi.fn(() => Promise.resolve([importBatch()])),
    detail: vi.fn(() => Promise.resolve(importBatchDetail())),
    errors: vi.fn(() =>
      Promise.resolve({ blob: new Blob(["e"]), fileName: "erreurs-IMP-000001.xlsx" }),
    ),
    cancel: vi.fn(() =>
      Promise.resolve(importBatch({ status: "cancelled", cancelled_at: "2026-11-14T08:00:00Z" })),
    ),
    ...overrides,
  };
}
