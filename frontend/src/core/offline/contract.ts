/**
 * Types de la synchronisation hors connexion (specs § 6.5), alias du contrat **généré**.
 * Un module léger : il ne charge pas Dexie (la base n'est ouverte que si le droit est actif).
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type SyncRequest = Schemas["SyncRequest"];
export type SyncOperationRequest = Schemas["SyncOperationRequest"];
export type SyncResponse = Schemas["SyncResponse"];
export type SyncResult = Schemas["SyncResultResponse"];
export type OfflineSnapshot = Schemas["OfflineSnapshotResponse"];

/** Saisies possibles hors connexion au Lot 1 (RG-T22 ; voyages au Lot 2). */
export type OperationType = "sale.create" | "expense.create";

/** Préfixe du numéro provisoire : `V` vente, `D` dépense (RG-T06). */
export type DocPrefix = "V" | "D";

export const PREFIX_OF: Readonly<Record<OperationType, DocPrefix>> = {
  "sale.create": "V",
  "expense.create": "D",
};

/** Une saisie en attente dans la file de l'appareil (IndexedDB, espacée par boutique). */
export interface QueuedOperation {
  /** Ordre de saisie (clé auto-incrémentée) : l'envoi suit cet ordre (RG-T23). */
  seq?: number;
  shopId: string;
  opId: string;
  type: OperationType;
  provisionalNumber: string;
  /** Heure de la saisie sur l'appareil, ISO avec fuseau (H12). */
  capturedAt: string;
  payload: Record<string, unknown>;
  status: "pending" | "rejected";
  /** Motif d'un refus du serveur, gardé et montré (RG-T23). */
  error: { code: string; message: string } | null;
}
