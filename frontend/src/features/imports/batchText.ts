/**
 * Textes des lots d'import (T45, design-system § 7.7) : « annulable jusqu'au JJ/MM », lignes
 * importées et ignorées, opérations qui bloquent une annulation (« la vente V-000003 »).
 * Un type d'opération inconnu ou une forme inattendue est une rupture de contrat : erreur.
 */
import type { ImportBatch } from "../../core/gateways/importsContract";
import { linesText } from "./importModels";

/** « 2026-11-20 » → « 20/11 ». */
export function dayMonth(day: string): string {
  const match = /^\d{4}-(\d{2})-(\d{2})$/.exec(day);
  if (match === null) throw new Error(`Date de lot invalide : « ${day} »`);
  return `${match[2] ?? ""}/${match[1] ?? ""}`;
}

/** Le lot peut encore être annulé à cette date (`today` : jour métier « AAAA-MM-JJ »). */
export function stillCancellable(batch: ImportBatch, today: string): boolean {
  return batch.status === "imported" && today <= batch.cancellable_until;
}

export const untilText = (batch: ImportBatch) =>
  `Annulable jusqu'au ${dayMonth(batch.cancellable_until)}`;

/** « 2 lignes importées, 1 ignorée ». */
export function rowsText(batch: ImportBatch): string {
  const imported = `${linesText(batch.rows_imported)} importée${batch.rows_imported > 1 ? "s" : ""}`;
  if (batch.rows_ignored === 0) return imported;
  return `${imported}, ${batch.rows_ignored.toLocaleString("fr-FR")} ignorée${batch.rows_ignored > 1 ? "s" : ""}`;
}

const BLOCKING_WORDS: Readonly<Record<string, string>> = {
  sale: "la vente",
  return: "le retour",
  purchase: "l'achat",
  adjustment: "l'ajustement",
  inventory: "l'inventaire",
  payment: "le versement",
  receivable: "la créance",
  import: "le lot",
};

/** `details.blocking` d'un refus `IMPORT_CANCEL_BLOCKED` → « la vente V-000003 », … */
export function blockingTexts(blocking: unknown): string[] {
  if (!Array.isArray(blocking)) throw new Error("details.blocking absent du refus d'annulation");
  return blocking.map((entry: unknown) => {
    if (typeof entry !== "object" || entry === null) {
      throw new Error("Opération bloquante illisible dans details.blocking");
    }
    const { type, number } = entry as { type?: unknown; number?: unknown };
    if (typeof type !== "string" || typeof number !== "string") {
      throw new Error("Opération bloquante sans type ou numéro dans details.blocking");
    }
    const word = BLOCKING_WORDS[type];
    if (word === undefined) throw new Error(`Type d'opération bloquante inconnu : « ${type} »`);
    return `${word} ${number}`;
  });
}
