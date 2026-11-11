/**
 * File d'envoi de l'appareil (TR-11, RG-T23) au-dessus de la base Dexie : ajout dans l'ordre
 * de saisie, lecture par boutique, retrait (accepté / doublon), refus gardé avec son motif,
 * compteur provisoire par boutique et appareil, instantané hors ligne.
 */
import type { DocPrefix, OfflineSnapshot, QueuedOperation } from "./contract";
import type { OfflineDb } from "./db";

export type NewOperation = Omit<QueuedOperation, "seq" | "status" | "error">;

export class Outbox {
  constructor(readonly db: OfflineDb) {}

  async enqueue(operation: NewOperation): Promise<void> {
    await this.db.operations.add({ ...operation, status: "pending", error: null });
  }

  /** Saisies d'une boutique dans l'ordre de saisie (`seq`). */
  private async ofShop(shopId: string, status: QueuedOperation["status"]) {
    return this.db.operations.where({ shopId, status }).sortBy("seq");
  }

  pending(shopId: string): Promise<QueuedOperation[]> {
    return this.ofShop(shopId, "pending");
  }

  rejected(shopId: string): Promise<QueuedOperation[]> {
    return this.ofShop(shopId, "rejected");
  }

  /** Tout ce qui attend sur l'appareil, toutes boutiques (blocage de la déconnexion, RG-T24). */
  async waiting(): Promise<number> {
    return this.db.operations.where("status").equals("pending").count();
  }

  async remove(opId: string): Promise<void> {
    await this.db.operations.where("opId").equals(opId).delete();
  }

  async reject(opId: string, error: { code: string; message: string }): Promise<void> {
    const changed = await this.db.operations
      .where("opId")
      .equals(opId)
      .modify({ status: "rejected", error });
    if (changed !== 1) throw new Error(`Opération ${opId} absente de la file`);
  }

  /** Abandon confirmé deux fois (RG-T24) : vide la file de l'appareil, renvoie le nombre perdu. */
  async discardAll(): Promise<number> {
    const count = await this.db.operations.count();
    await this.db.operations.clear();
    return count;
  }

  /** Séquence suivante, dans une transaction (deux saisies rapides n'ont jamais le même n°). */
  nextSequence(shopId: string, deviceId: string, prefix: DocPrefix): Promise<number> {
    const key = `${shopId}|${deviceId}|${prefix}`;
    return this.db.transaction("rw", this.db.counters, async () => {
      const value = ((await this.db.counters.get(key))?.value ?? 0) + 1;
      await this.db.counters.put({ key, value });
      return value;
    });
  }

  async saveSnapshot(shopId: string, body: OfflineSnapshot, now: Date): Promise<void> {
    await this.db.snapshots.put({ shopId, body, savedAt: now.toISOString() });
  }

  async snapshot(shopId: string): Promise<OfflineSnapshot | null> {
    return (await this.db.snapshots.get(shopId))?.body ?? null;
  }
}
