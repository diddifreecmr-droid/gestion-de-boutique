/**
 * Import Excel pour les tests : réponses typées par le contrat généré (aperçu, lot) et modules
 * de boutique **forcés** (le module `import` est à venir : jamais actif dans l'application
 * avant T46). Réservé aux tests.
 */
import type {
  ImportBatch,
  ImportBatchDetail,
  ImportPreview,
} from "../core/gateways/importsContract";
import { ALL_MODULES, type ModuleCode, type ShopModules } from "../core/profile/modules";

export const PREVIEW_ID = "prev-01890a5d-ac96";

export function importPreview(overrides: Partial<ImportPreview> = {}): ImportPreview {
  return {
    preview_id: PREVIEW_ID,
    kind: "articles",
    expires_at: "2026-11-13T10:30:00Z",
    rows_read: 4,
    rows_valid: 2,
    rows_ignored: 2,
    problems: [
      {
        line: 3,
        column: "Nom",
        message: "doublon",
        text: "Ligne 3 : l'article « CH » existe déjà (ignoré)",
      },
      { line: 5, column: "Nom", message: "vide", text: "Ligne 5 : le nom est vide" },
    ],
    problems_total: 2,
    notes: ["2 articles nouveaux seront créés"],
    ...overrides,
  };
}

export function importBatch(overrides: Partial<ImportBatch> = {}): ImportBatch {
  return {
    id: "batch-1",
    number: "IMP-000001",
    kind: "articles",
    status: "imported",
    rows_read: 4,
    rows_imported: 2,
    rows_ignored: 2,
    created: [{ entity: "article", count: 2 }],
    imported_at: "2026-11-13T10:05:00Z",
    cancellable_until: "2026-11-20",
    cancelled_at: null,
    ...overrides,
  };
}

export function importBatchDetail(overrides: Partial<ImportBatchDetail> = {}): ImportBatchDetail {
  return {
    ...importBatch(),
    imported_by: { id: "u-owner", name: "Awa Propriétaire" },
    problems_total: 2,
    items: [
      { line: 2, entity: "article", entity_id: "a-1" },
      { line: 4, entity: "article", entity_id: "a-2" },
    ],
    ...overrides,
  };
}

/** Modules de boutique tels que la coquille les fournirait, `import` compris (forcé). */
export function forcedModules(off: readonly ModuleCode[] = []): ShopModules {
  const enabled = new Set<ModuleCode>(ALL_MODULES.filter((module) => !off.includes(module)));
  return { enabled, has: (module) => enabled.has(module) };
}
