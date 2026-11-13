/**
 * Modules d'une boutique (décisions client des 12 et 13/11/2026, specs § 15.1) : seul
 * l'administrateur plateforme les active. Toujours actifs : `core`, `audit`, `catalog`, `sales`.
 * Facultatifs disponibles : `purchases`, `receivables`, `expenses`, `dashboard`. **À venir**
 * (pas encore construits, Lot 2/3) : `transfers`, `transport`, `import` — jamais activables,
 * jamais montrés comme actifs (on ne montre jamais ce qui n'existe pas). Un module éteint :
 * **tous** ses points d'entrée disparaissent ; ses données sont gardées.
 */
import type { components } from "../api/schema.gen";
import { ApiError } from "../api/errors";

export type ModuleCode = components["schemas"]["Module"];

export const ALWAYS_ON = [
  "core",
  "audit",
  "catalog",
  "sales",
] as const satisfies readonly ModuleCode[];
export type OptionalModule = Exclude<ModuleCode, (typeof ALWAYS_ON)[number]>;

/** Pas encore construits (miroir de `UPCOMING_MODULES` du serveur : 422 `MODULE_NOT_YET_AVAILABLE`). */
export const UPCOMING_MODULES = [
  "transfers",
  "transport",
  "import",
] as const satisfies readonly OptionalModule[];
export type UpcomingModule = (typeof UPCOMING_MODULES)[number];

/** Facultatifs construits, activables par interrupteur ; ordre d'affichage dans la console. */
export const AVAILABLE_OPTIONAL_MODULES = [
  "purchases",
  "receivables",
  "expenses",
  "dashboard",
] as const satisfies readonly Exclude<OptionalModule, UpcomingModule>[];

export const OPTIONAL_MODULES: readonly OptionalModule[] = [
  ...AVAILABLE_OPTIONAL_MODULES,
  ...UPCOMING_MODULES,
];

/** Vérifié à la compilation : chaque module du contrat est classé (toujours actif, facultatif, à venir). */
type Unclassified = Exclude<
  OptionalModule,
  (typeof AVAILABLE_OPTIONAL_MODULES)[number] | UpcomingModule
>;
type AssertNever<T extends never> = T;
export type ModulesAreClassified = AssertNever<Unclassified>;

export const ALL_MODULES: readonly ModuleCode[] = [...ALWAYS_ON, ...OPTIONAL_MODULES];

/** `module ⇒ prérequis` : le module ne peut être actif sans son prérequis. */
export const REQUIRES: Readonly<Partial<Record<OptionalModule, OptionalModule>>> = {
  transport: "transfers",
};

export function isUpcoming(module: ModuleCode): module is UpcomingModule {
  return UPCOMING_MODULES.some((upcoming) => upcoming === module);
}

export interface ShopModules {
  readonly enabled: ReadonlySet<ModuleCode>;
  has: (module: ModuleCode) => boolean;
}

function isModule(code: string): code is ModuleCode {
  return ALL_MODULES.some((known) => known === code);
}

/** Code de module lu de l'API ; un code inconnu est une rupture de contrat (fail-fast). */
export function parseModule(code: string): ModuleCode {
  if (!isModule(code)) {
    throw new Error(
      `Module inconnu reçu de l'API : « ${code} » (attendu ${ALL_MODULES.join(", ")})`,
    );
  }
  return code;
}

/**
 * Modules actifs lus du serveur (`enabled_modules`). Un code inconnu est une rupture de contrat
 * (fail-fast). Les modules toujours actifs sont ajoutés : sans eux l'application ne tourne pas.
 * Un module à venir n'est **jamais** actif côté client, même porté par une ancienne réponse
 * gardée hors connexion (avant la migration `0016_upcoming_modules`) : il est écarté, par règle.
 */
export function shopModules(codes: readonly string[]): ShopModules {
  const enabled = new Set<ModuleCode>(ALWAYS_ON);
  for (const code of codes.map(parseModule)) {
    if (!isUpcoming(code)) enabled.add(code);
  }
  return { enabled, has: (module) => enabled.has(module) };
}

/** Code d'erreur du serveur pour une route d'un module éteint (403). */
export const MODULE_DISABLED = "MODULE_DISABLED";
export const MODULE_DISABLED_MESSAGE = "Cette fonction n'est pas activée pour cette boutique.";

export function isModuleDisabled(error: unknown): error is ApiError {
  return error instanceof ApiError && error.code === MODULE_DISABLED;
}
