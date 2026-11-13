/**
 * Mots de la console pour les modules d'une boutique (décisions client des 12 et 13/11/2026) :
 * nom, dépendance et effet d'un changement, dits avant d'enregistrer.
 */
import {
  ALWAYS_ON,
  isUpcoming,
  OPTIONAL_MODULES,
  REQUIRES,
  type ModuleCode,
  type OptionalModule,
} from "../../core/profile/modules";

export const MODULE_LABELS: Readonly<Record<ModuleCode, string>> = {
  core: "Socle (membres, lieux, réglages)",
  audit: "Journal d'actions",
  catalog: "Catalogue et stock",
  sales: "Ventes et reçus",
  purchases: "Achats",
  receivables: "Créances",
  expenses: "Dépenses",
  transfers: "Transferts",
  transport: "Transport",
  dashboard: "Tableau de bord",
  import: "Import Excel",
};

/** Ce qui disparaît de la boutique quand le module est désactivé. */
const LOSSES: Readonly<Record<OptionalModule, string>> = {
  purchases: "plus d'achats, de fournisseurs ni de paiements fournisseur",
  receivables: "plus de vente à crédit, de versements ni de garants",
  expenses: "plus de saisie de dépenses, et aucune dépense dans les chiffres",
  transfers: "plus de déplacements de stock entre lieux",
  transport: "plus de camions, de voyages, de dépenses de voyage ni de paie des chauffeurs",
  dashboard: "plus de chiffres détaillés du tableau de bord",
  import: "plus d'import d'articles depuis un fichier Excel",
};

const KEPT = "Les données sont gardées.";

/** Noms courts des modules toujours actifs, réunis sur une seule ligne compacte de la fiche. */
const ALWAYS_ON_SHORT: Readonly<Record<(typeof ALWAYS_ON)[number], string>> = {
  core: "Socle",
  audit: "Journal",
  catalog: "Catalogue et stock",
  sales: "Ventes",
};

/** « Toujours actifs : Socle, Journal, Catalogue et stock, Ventes ». */
export const ALWAYS_ON_LINE = `Toujours actifs : ${ALWAYS_ON.map((m) => ALWAYS_ON_SHORT[m]).join(", ")}`;

/** Modules facultatifs qui ont besoin de `module` (ex. Transport a besoin de Transferts). */
export function dependentsOf(module: OptionalModule): OptionalModule[] {
  return OPTIONAL_MODULES.filter((other) => REQUIRES[other] === module);
}

/** Phrase sous l'interrupteur : la dépendance, dite dans les deux sens. */
export function dependencyHint(module: OptionalModule): string | undefined {
  const needs = REQUIRES[module];
  if (needs !== undefined) {
    return `A besoin de ${MODULE_LABELS[needs]} : l'activer active aussi ${MODULE_LABELS[needs]}.`;
  }
  const dependents = dependentsOf(module).map((other) => MODULE_LABELS[other]);
  if (dependents.length === 0) return undefined;
  return `Le désactiver désactive aussi ${dependents.join(", ")}.`;
}

/** Nouveau jeu de modules après un appui, dépendances comprises. */
export function toggle(
  enabled: ReadonlySet<ModuleCode>,
  module: OptionalModule,
  on: boolean,
): Set<ModuleCode> {
  const next = new Set(enabled);
  if (on) {
    next.add(module);
    const needs = REQUIRES[module];
    if (needs !== undefined) next.add(needs);
  } else {
    next.delete(module);
    for (const dependent of dependentsOf(module)) next.delete(dependent);
  }
  for (const always of ALWAYS_ON) next.add(always);
  return next;
}

/** Phrases dites avant d'enregistrer : un module désactivé, puis un module activé, par ligne. */
export function changeSummary(
  before: ReadonlySet<ModuleCode>,
  after: ReadonlySet<ModuleCode>,
): string[] {
  const off = OPTIONAL_MODULES.filter((m) => before.has(m) && !after.has(m));
  const on = OPTIONAL_MODULES.filter((m) => !before.has(m) && after.has(m));
  return [
    ...off.map((m) => `${MODULE_LABELS[m]} désactivé : ${LOSSES[m]}. ${KEPT}`),
    ...on.map((m) => `${MODULE_LABELS[m]} activé : ses écrans et ses données réapparaissent.`),
  ];
}

/**
 * Liste envoyée au serveur (`PATCH … { modules }`) : le jeu complet, dans l'ordre du contrat ;
 * jamais un module à venir (le serveur le refuserait : 422 `MODULE_NOT_YET_AVAILABLE`).
 */
export function modulesBody(enabled: ReadonlySet<ModuleCode>): ModuleCode[] {
  return [...ALWAYS_ON, ...OPTIONAL_MODULES].filter((m) => enabled.has(m) && !isUpcoming(m));
}
