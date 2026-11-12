/**
 * Passerelle du Journal (UC-JRN-01, specs § 6.3) : consultation **seule** — le journal est en
 * ajout seul (RG-J01), aucune route ne le modifie. Types issus du contrat **généré**.
 *
 * Droits (serveur) : propriétaire seul (`AUDIT_READ`, 403 sinon). Le serveur renvoie des champs
 * structurés (auteur, rôle, action, élément, changements) ; la phrase est composée ici avec les
 * noms des membres (`GET /members`, propriétaire seul lui aussi).
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type AuditEntry = Schemas["AuditEntryResponse"];
export type AuditPage = Schemas["AuditPageResponse"];
export type AuditAction = Schemas["AuditAction"];
export type JournalMember = Schemas["MemberResponse"];

/** Filtres de `GET /audit` ; `null` = filtre absent. Dates au format AAAA-MM-JJ. */
export interface JournalQuery {
  from: string | null;
  to: string | null;
  userId: string | null;
  action: AuditAction | null;
  module: string | null;
  cursor: string | null;
}

export interface JournalGateway {
  /** Les plus récentes en haut ; `next_cursor` pour la suite. */
  list(shopId: string, query: JournalQuery): Promise<AuditPage>;
  members(shopId: string): Promise<JournalMember[]>;
}
