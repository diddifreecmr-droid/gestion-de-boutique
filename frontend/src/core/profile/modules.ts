/**
 * Modules d'une boutique (décision client du 12/11/2026, specs § 15.1) : seul l'administrateur
 * plateforme les active. Toujours actifs : `core`, `audit`, `catalog`, `sales`. Facultatifs :
 * les sept autres, avec la dépendance `transport` ⇒ `transfers`. Un module éteint : **tous** ses
 * points d'entrée disparaissent ; ses données sont gardées.
 */
import type { components } from "../api/schema.gen";
import { ApiError } from "../api/errors";

export type ModuleCode = components["schemas"]["Module"];

export const ALWAYS_ON = ["core", "audit", "catalog", "sales"] as const satisfies readonly ModuleCode[];
export type OptionalModule = Exclude<ModuleCode, (typeof ALWAYS_ON)[number]>;

/** Ordre d'affichage dans la console. */
export const OPTIONAL_MODULES = [
  "purchases",
  "receivables",
  "expenses",
  "transfers",
  "transport",
  "dashboard",
  "import",
] as const satisfies readonly OptionalModule[];

/** Vérifié à la compilation : chaque module du contrat est classé (toujours actif ou facultatif). */
type Unclassified = Exclude<OptionalModule, (typeof OPTIONAL_MODULES)[number]>;
type AssertNever<T extends never> = T;
export type ModulesAreClassified = AssertNever<Unclassified>;

export const ALL_MODULES: readonly ModuleCode[] = [...ALWAYS_ON, ...OPTIONAL_MODULES];

/** `module ⇒ prérequis` : le module ne peut être actif sans son prérequis. */
export const REQUIRES: Readonly<Partial<Record<OptionalModule, OptionalModule>>> = {
  transport: "transfers",
};

export interface ShopModules {
  readonly enabled: ReadonlySet<ModuleCode>;
  has: (module: ModuleCode) => boolean;
}

function isModule(code: string): code is ModuleCode {
  return ALL_MODULES.some((known) => known === code);
}

/**
 * Modules actifs lus du serveur (`enabled_modules`). Un code inconnu est une rupture de contrat
 * (fail-fast). Les modules toujours actifs sont ajoutés : sans eux l'application ne tourne pas.
 */
export function shopModules(codes: readonly string[]): ShopModules {
  const enabled = new Set<ModuleCode>(ALWAYS_ON);
  for (const code of codes) {
    if (!isModule(code)) {
      throw new Error(`Module inconnu reçu de l'API : « ${code} » (attendu ${ALL_MODULES.join(", ")})`);
    }
    enabled.add(code);
  }
  return { enabled, has: (module) => enabled.has(module) };
}

/** Code d'erreur du serveur pour une route d'un module éteint (403). */
export const MODULE_DISABLED = "MODULE_DISABLED";
export const MODULE_DISABLED_MESSAGE = "Cette fonction n'est pas activée pour cette boutique.";

export function isModuleDisabled(error: unknown): error is ApiError {
  return error instanceof ApiError && error.code === MODULE_DISABLED;
}
