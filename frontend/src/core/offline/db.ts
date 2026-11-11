/**
 * Base IndexedDB de l'appareil (Dexie, specs § 7.2) — chargée **à la demande** seulement si
 * le droit `offline_capture` est actif (aucun octet de Dexie dans le premier chargement).
 *
 * Versions (une migration ne vide **jamais** la file, specs § 7.3, recette OFF-10) :
 * - 1 : `operations` (file d'envoi, ordre `seq`), `counters` (numéros provisoires) ;
 * - 2 : `status` / `error` sur chaque opération (refus gardés), index `status`
 *   et `[shopId+status]`,
 *   `snapshots` (instantané hors ligne par boutique, RG-T25). Les opérations de la version 1
 *   passent `pending`.
 */
import { Dexie, type EntityTable } from "dexie";
import type { OfflineSnapshot, QueuedOperation } from "./contract";

export const DB_NAME = "boutique-offline";

export const SCHEMA_V1 = { operations: "++seq, shopId, &opId", counters: "key" };
export const SCHEMA_V2 = {
  operations: "++seq, shopId, &opId, status, [shopId+status]",
  counters: "key",
  snapshots: "shopId",
};

export interface Counter {
  /** `<boutique>|<appareil>|<préfixe>` : compteur provisoire par boutique et appareil. */
  key: string;
  value: number;
}

export interface StoredSnapshot {
  shopId: string;
  body: OfflineSnapshot;
  savedAt: string;
}

export type OfflineDb = Dexie & {
  operations: EntityTable<QueuedOperation, "seq">;
  counters: EntityTable<Counter, "key">;
  snapshots: EntityTable<StoredSnapshot, "shopId">;
};

export function openOfflineDb(name: string = DB_NAME): OfflineDb {
  const db = new Dexie(name) as OfflineDb;
  db.version(1).stores(SCHEMA_V1);
  db.version(2)
    .stores(SCHEMA_V2)
    .upgrade((tx) =>
      tx
        .table<Partial<QueuedOperation>>("operations")
        .toCollection()
        .modify((operation) => {
          operation.status ??= "pending";
          operation.error ??= null;
        }),
    );
  return db;
}
