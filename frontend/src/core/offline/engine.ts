/**
 * Point d'entrée **chargé à la demande** (`import("./engine")`) : seul module qui importe
 * Dexie. N'est jamais chargé tant que le droit `offline_capture` est inactif (V1).
 */
import { openOfflineDb } from "./db";
import { Outbox } from "./outbox";

export { sendQueue } from "./sendQueue";
export { Outbox };

export function openOutbox(name?: string): Outbox {
  return new Outbox(openOfflineDb(name));
}
