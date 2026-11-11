/**
 * Brouillon de la saisie d'un achat (UC-ACH-01, UC-ACH-03) et ses contrôles. Le serveur reste
 * juge (dates, références actives, écart de prix) ; l'écran prévient avant d'envoyer.
 */
import { uuidV7 } from "../../core/api/uuidv7";
import type { ArticleResponse } from "../../core/gateways/catalogAdminContract";
import type { EntryUnit, FeeKind, Purchase } from "../../core/gateways/purchasingContract";
import { dateProblem } from "../expenses/businessDay";
import { feeKind } from "./fees";
import { entryUnit, parseEntryQuantity, quantityInput, type UnitArticle } from "./units";

/** Article d'une ligne : ce qu'il faut pour proposer l'unité et chiffrer la ligne. */
export interface DraftArticle extends UnitArticle {
  id: string;
  name: string;
}

export interface LineDraft {
  key: string;
  article: DraftArticle | null;
  quantity: string;
  unit: EntryUnit | null;
  unitPrice: number | null;
}

export interface FeeDraft {
  key: string;
  kind: FeeKind;
  amount: number | null;
  label: string;
}

/** `locationId` vide : lieu de réception par défaut des réglages (choisi par le serveur). */
export interface PurchaseDraft {
  supplier: { id: string; name: string } | null;
  date: string;
  locationId: string;
  lines: LineDraft[];
  fees: FeeDraft[];
  invoiceRef: string;
  note: string;
}

export interface LineProblems {
  article?: string;
  quantity?: string;
  price?: string;
}

export interface DraftProblems {
  date?: string;
  lines: Record<string, LineProblems>;
  fees: Record<string, string>;
}

export const DEFAULT_LOCATION = "";

export function draftArticle(article: ArticleResponse): DraftArticle {
  return {
    id: article.id,
    name: article.display_name,
    stock_unit: article.stock_unit,
    sold_by_piece: article.sold_by_piece,
    piece_length_m: article.piece_length_m,
  };
}

export function emptyLine(): LineDraft {
  return { key: uuidV7(), article: null, quantity: "", unit: null, unitPrice: null };
}

export function emptyFee(kind: FeeKind): FeeDraft {
  return { key: uuidV7(), kind, amount: null, label: "" };
}

export function emptyDraft(today: string, locationId: string): PurchaseDraft {
  return {
    supplier: null,
    date: today,
    locationId,
    lines: [emptyLine()],
    fees: [],
    invoiceRef: "",
    note: "",
  };
}

/** Brouillon de correction ; `articles` donne le nom et l'unité de chaque article de l'achat. */
export function draftOf(
  purchase: Purchase,
  supplierName: string | null,
  articles: ReadonlyMap<string, DraftArticle>,
): PurchaseDraft {
  const article = (id: string) => {
    const found = articles.get(id);
    if (found === undefined) throw new Error(`Article de l'achat non chargé : « ${id} »`);
    return found;
  };
  return {
    supplier:
      purchase.supplier_id === null || supplierName === null
        ? null
        : { id: purchase.supplier_id, name: supplierName },
    date: purchase.purchase_date,
    locationId: purchase.location_id,
    lines: purchase.lines.map((line) => ({
      key: uuidV7(),
      article: article(line.article_id),
      quantity: quantityInput(line.quantity),
      unit: entryUnit(line.unit),
      unitPrice: line.unit_price,
    })),
    fees: purchase.fees.map((fee) => ({
      key: uuidV7(),
      kind: feeKind(fee.kind),
      amount: fee.amount,
      label: fee.label ?? "",
    })),
    invoiceRef: purchase.invoice_ref ?? "",
    note: purchase.note ?? "",
  };
}

function lineProblems(line: LineDraft, duplicate: boolean): LineProblems {
  const problems: LineProblems = {};
  if (line.article === null) problems.article = "Choisissez l'article";
  else if (duplicate) problems.article = "Cet article figure déjà sur une autre ligne";
  if (line.unit !== null) {
    const parsed = parseEntryQuantity(line.quantity, line.unit);
    if (!parsed.ok) problems.quantity = parsed.error;
  }
  if (line.unitPrice === null) problems.price = "Le prix unitaire est vide";
  return problems;
}

export function draftProblems(
  draft: PurchaseDraft,
  today: string,
  isOwner: boolean,
): DraftProblems {
  const problems: DraftProblems = { lines: {}, fees: {} };
  const date = dateProblem(draft.date, today, isOwner);
  if (date !== undefined) problems.date = date;
  const seen = new Set<string>();
  for (const line of draft.lines) {
    const id = line.article?.id;
    const found = lineProblems(line, id !== undefined && seen.has(id));
    if (id !== undefined) seen.add(id);
    if (Object.keys(found).length > 0) problems.lines[line.key] = found;
  }
  for (const fee of draft.fees) {
    if (fee.amount === null) problems.fees[fee.key] = "Le montant des frais est vide";
    else if (fee.kind === "other" && fee.label.trim() === "") {
      problems.fees[fee.key] = "Les frais « Autre » exigent un libellé";
    }
  }
  return problems;
}

export function hasProblems(problems: DraftProblems): boolean {
  return (
    problems.date !== undefined ||
    Object.keys(problems.lines).length > 0 ||
    Object.keys(problems.fees).length > 0
  );
}
