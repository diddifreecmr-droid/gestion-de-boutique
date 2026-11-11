import type { Movement } from "../../core/gateways/stockContract";

/** Nature du document lié (backend `SourceType`). */
const DOCUMENTS: Readonly<Record<string, string>> = {
  purchase: "Achat",
  sale: "Vente",
  return: "Retour client",
  transfer: "Déplacement",
  adjustment: "Ajustement",
  inventory: "Inventaire",
  import: "Import",
};

/**
 * Document lié : son numéro (`A-000001`, `INV-000001`) quand il en a un, sinon sa nature.
 * Le comptable ne reçoit pas le numéro d'une vente (RG-D03) : il lit « Vente ».
 */
export function documentLabel(document: Movement["document"]): string {
  const kind = DOCUMENTS[document.type];
  if (kind === undefined) throw new Error(`Document lié inconnu : « ${document.type} »`);
  return document.number === null ? kind : `${kind} ${document.number}`;
}
