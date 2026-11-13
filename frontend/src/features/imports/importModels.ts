/**
 * Modèles d'import du Lot 3 (UC-IMP-01, specs § 6.3, matrice § 4.2) : 5 modèles. Le comptable
 * en voit 3 (articles, stock de départ, fournisseurs) ; clients et créances : propriétaire seul.
 * Un modèle qui exige un module éteint (créances → `receivables`, fournisseurs → `purchases`)
 * n'est pas montré : le serveur le refuserait (403 `MODULE_DISABLED`, IMP-11).
 */
import type { Role } from "../../core/auth/me";
import type { ImportedEntity, ImportKind } from "../../core/gateways/importsContract";
import type { ModuleCode, ShopModules } from "../../core/profile/modules";

export interface ImportModel {
  kind: ImportKind;
  label: string;
  /** Ce que contient le modèle, en mots simples. */
  description: string;
  roles: readonly Role[];
  /** Module exigé en plus de `import` (`null` : aucun). */
  module: ModuleCode | null;
}

const OWNER_ACCOUNTANT: readonly Role[] = ["owner", "accountant"];

export const IMPORT_MODELS: readonly ImportModel[] = [
  {
    kind: "articles",
    label: "Articles",
    description: "Nom, prix, catégorie de chaque article",
    roles: OWNER_ACCOUNTANT,
    module: null,
  },
  {
    kind: "opening_stock",
    label: "Stock de départ",
    description: "Quantité en main et coût, lieu par lieu",
    roles: OWNER_ACCOUNTANT,
    module: null,
  },
  {
    kind: "customers",
    label: "Clients",
    description: "Nom, téléphone et type de chaque client",
    roles: ["owner"],
    module: null,
  },
  {
    kind: "receivables",
    label: "Créances en cours",
    description: "Ce que vos clients vous doivent déjà",
    roles: ["owner"],
    module: "receivables",
  },
  {
    kind: "suppliers",
    label: "Fournisseurs",
    description: "Nom et téléphone de chaque fournisseur",
    roles: OWNER_ACCOUNTANT,
    module: "purchases",
  },
];

/** Rôles qui ont au moins un modèle : les autres n'ont pas d'écran d'import. */
export const IMPORT_ROLES: readonly Role[] = ["owner", "accountant"];

/** Modèles proposés à ce rôle, dans cette boutique. */
export function modelsFor(role: Role, modules: ShopModules): ImportModel[] {
  return IMPORT_MODELS.filter(
    (model) => model.roles.includes(role) && (model.module === null || modules.has(model.module)),
  );
}

/** Modèle d'un code reçu du serveur ; inconnu → rupture de contrat (fail-fast). */
export function modelOf(kind: ImportKind): ImportModel {
  const found = IMPORT_MODELS.find((model) => model.kind === kind);
  if (found === undefined) throw new Error(`Modèle d'import inconnu : « ${kind} »`);
  return found;
}

/** Nom des éléments créés, au singulier et au pluriel (rapport d'import). */
const ENTITY_WORDS: Readonly<Record<ImportedEntity, readonly [string, string]>> = {
  article: ["article créé", "articles créés"],
  stock_movement: ["entrée de stock de départ", "entrées de stock de départ"],
  customer: ["client créé", "clients créés"],
  receivable: ["créance enregistrée", "créances enregistrées"],
  supplier: ["fournisseur créé", "fournisseurs créés"],
};

/** « 3 articles créés », « 1 client créé ». */
export function createdText(entity: ImportedEntity, count: number): string {
  const [one, many] = ENTITY_WORDS[entity];
  return `${count.toLocaleString("fr-FR")} ${count > 1 ? many : one}`;
}

/** « 1 ligne », « 48 lignes ». */
export function linesText(count: number): string {
  return `${count.toLocaleString("fr-FR")} ligne${count > 1 ? "s" : ""}`;
}
