/**
 * Envoi de la file d'une boutique (specs § 6.5) : opérations **dans l'ordre**, par lots de 20,
 * `POST /sync`. Résultat par opération : `accepted` / `duplicate` → retirée de la file et
 * message « Vente V-HL-3F2A-0007 → V-000125 » ; `rejected` → gardée avec son motif (RG-T23).
 * Une réponse sans résultat pour une opération envoyée est une rupture de contrat (fail-fast).
 * `NetworkError` remonte : la file reste intacte, l'envoi reprendra au retour du réseau.
 */
import type { QueuedOperation, SyncRequest, SyncResponse } from "./contract";
import type { Outbox } from "./outbox";

export const BATCH_SIZE = 20;

export type SendBatch = (shopId: string, body: SyncRequest) => Promise<SyncResponse>;

export interface SentReport {
  /** Une phrase par saisie arrivée : « Vente V-HL-… → V-000125 ». */
  arrived: string[];
  rejected: number;
}

const LABEL: Readonly<Record<QueuedOperation["type"], string>> = {
  "sale.create": "Vente",
  "expense.create": "Dépense",
};

function request(deviceId: string, batch: readonly QueuedOperation[]): SyncRequest {
  return {
    device_id: deviceId,
    operations: batch.map((op) => ({
      op_id: op.opId,
      type: op.type,
      provisional_number: op.provisionalNumber,
      captured_at: op.capturedAt,
      payload: op.payload,
    })),
  };
}

export async function sendQueue(
  outbox: Outbox,
  send: SendBatch,
  shopId: string,
  deviceId: string,
): Promise<SentReport> {
  const report: SentReport = { arrived: [], rejected: 0 };
  for (;;) {
    const batch = (await outbox.pending(shopId)).slice(0, BATCH_SIZE);
    if (batch.length === 0) return report;
    const { results } = await send(shopId, request(deviceId, batch));
    for (const op of batch) {
      const result = results.find((r) => r.op_id === op.opId);
      if (result === undefined) throw new Error(`Réponse de /sync sans résultat pour ${op.opId}`);
      if (result.status === "rejected") {
        if (result.error === null) throw new Error(`Refus sans motif pour ${op.opId}`);
        await outbox.reject(op.opId, { code: result.error.code, message: result.error.message });
        report.rejected += 1;
        continue;
      }
      if (result.number === null) throw new Error(`Numéro définitif absent pour ${op.opId}`);
      await outbox.remove(op.opId);
      report.arrived.push(`${LABEL[op.type]} ${op.provisionalNumber} → ${result.number}`);
    }
  }
}
