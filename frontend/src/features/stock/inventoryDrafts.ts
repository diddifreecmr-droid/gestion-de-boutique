/**
 * Comptage d'un inventaire en cours (UC-STK-07, INV-01) : quantités tapées par article, et ce
 * qu'il faut envoyer (`PUT /counts`, seulement les lignes changées). La ligne d'un inventaire
 * en cours ne porte **que** la quantité comptée : aucune quantité théorique n'est lue ici.
 */
import type { Inventory } from "../../core/gateways/stockContract";
import { parseQuantity, toInput } from "./quantities";

export type Drafts = Readonly<Record<string, string>>;

export interface CountEntry {
  article_id: string;
  counted: string | null;
}

export function initialDrafts(inventory: Inventory): Drafts {
  return Object.fromEntries(
    inventory.lines.map((line) => [line.article_id, toInput(line.counted)]),
  );
}

function sameCount(sent: string | null, server: string | null): boolean {
  if (sent === null || server === null) return sent === server;
  return Number(sent) === Number(server);
}

/** Lignes changées depuis la dernière lecture, et erreurs de saisie par article. */
export function pendingCounts(inventory: Inventory, drafts: Drafts) {
  const entries: CountEntry[] = [];
  const errors: Record<string, string> = {};
  for (const line of inventory.lines) {
    const text = (drafts[line.article_id] ?? "").trim();
    let counted: string | null = null;
    if (text !== "") {
      const parsed = parseQuantity(text, line.stock_unit, true);
      if (!parsed.ok) {
        errors[line.article_id] = parsed.error;
        continue;
      }
      counted = parsed.value;
    }
    if (!sameCount(counted, line.counted)) entries.push({ article_id: line.article_id, counted });
  }
  return { entries, errors };
}

/** Articles encore sans quantité tapée. */
export function uncounted(inventory: Inventory, drafts: Drafts): number {
  return inventory.lines.filter((line) => (drafts[line.article_id] ?? "").trim() === "").length;
}
