/**
 * Phrase du journal (AUD-01) : « 10/11/2026 14 h 32 — Paul (Vendeur) a créé la vente
 * V-000124 : 1 moto Haojue HJ125-8, 780 000 FCFA ». Le serveur donne les champs structurés ;
 * les noms viennent des membres, les libellés de rôle du profil de la boutique.
 * Un code inconnu (action, élément, module) reste affiché tel quel, jamais masqué.
 */
import type { AuditAction, AuditEntry } from "../../core/gateways/journalContract";
import { formatDate, formatTime } from "../../shared/format";

export const ACTION_LABELS: Readonly<Record<AuditAction, string>> = {
  create: "Créer",
  update: "Modifier",
  cancel: "Annuler",
  validate: "Valider",
  reject: "Rejeter",
  login: "Se connecter",
  logout: "Se déconnecter",
  print: "Imprimer",
  import: "Importer",
  configure: "Régler",
  access_denied: "Accès refusé",
};

const VERBS: Readonly<Record<string, string>> = {
  create: "a créé",
  update: "a modifié",
  cancel: "a annulé",
  validate: "a validé",
  reject: "a rejeté",
  login: "s'est connecté à",
  logout: "s'est déconnecté de",
  print: "a imprimé",
  import: "a importé",
  configure: "a réglé",
  access_denied: "s'est vu refuser l'accès à",
};

const NOUNS: Readonly<Record<string, string>> = {
  sale: "la vente",
  article: "l'article",
  customer: "le client",
  receivable: "la créance",
  installment: "le versement",
  purchase: "l'achat",
  supplier: "le fournisseur",
  expense: "la dépense",
  expense_category: "la catégorie de dépense",
  tag: "l'étiquette",
  adjustment: "l'ajustement",
  inventory: "l'inventaire",
  location: "le lieu",
  payment_mode: "le mode de paiement",
  price_request: "la demande de prix",
  shop: "la boutique",
  shop_settings: "les réglages",
  user: "l'utilisateur",
  admin_access: "l'accès de l'administrateur",
  permission: "la permission",
  sync_operation: "la saisie hors connexion",
};

export const MODULE_LABELS: Readonly<Record<string, string>> = {
  sales: "Ventes",
  catalog: "Catalogue",
  stock: "Stock",
  purchases: "Achats",
  expenses: "Dépenses",
  receivables: "Créances",
  members: "Utilisateurs",
  shop: "Boutique",
  platform: "Plateforme",
  identity: "Connexion",
  security: "Sécurité",
  sync: "Hors connexion",
};

/** Libellé du rôle **au moment de l'action** ; l'administrateur n'a pas de rôle de boutique. */
export type RoleLabel = (role: string) => string;

export interface People {
  nameOf: (userId: string) => string | undefined;
  roleLabel: RoleLabel;
}

export function moduleLabel(module: string): string {
  return MODULE_LABELS[module] ?? module;
}

function author(entry: AuditEntry, people: People): string {
  const role = people.roleLabel(entry.performer.role);
  const name = people.nameOf(entry.performer.user_id) ?? "Utilisateur inconnu";
  return `${name} (${role})`;
}

function element(entry: AuditEntry): string {
  const noun = NOUNS[entry.entity.type] ?? entry.entity.type;
  return entry.entity.number === null ? noun : `${noun} ${entry.entity.number}`;
}

/** « 10/11/2026 14 h 32 » : l'heure de la saisie sur l'appareil (RG-T04). */
export function entryMoment(entry: AuditEntry): string {
  return `${formatDate(entry.captured_at)} ${formatTime(entry.captured_at)}`;
}

/** « Paul (Vendeur) a créé la vente V-000124 : 1 moto…, 780 000 FCFA ». */
export function entrySentence(entry: AuditEntry, people: People): string {
  const verb = VERBS[entry.action] ?? entry.action_label;
  const head = `${author(entry, people)} ${verb} ${element(entry)}`;
  return entry.summary.trim() === "" ? head : `${head} : ${entry.summary}`;
}

/** Valeur avant/après lisible ; `null` = « (vide) ». */
export function changeValue(value: string | number | boolean | null): string {
  if (value === null) return "(vide)";
  if (typeof value === "boolean") return value ? "oui" : "non";
  return String(value);
}
