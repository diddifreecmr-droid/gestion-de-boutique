/**
 * Brouillon du formulaire de dépense (UC-DEP-01, UC-DEP-04, UC-DEP-05) et ses contrôles.
 * Le serveur reste juge (description, dates, références actives) ; l'écran prévient avant.
 */
import type {
  Expense,
  ExpenseCreate,
  ExpenseDraft,
  ExpensePatch,
} from "../../core/gateways/expensesContract";
import { dateProblem } from "./businessDay";
import type { References } from "./references";

export interface Draft {
  amount: number | null;
  categoryId: string | null;
  tags: readonly string[];
  description: string;
  locationId: string | null;
  beneficiary: string;
  modeId: string | null;
  date: string;
}

export interface DraftProblems {
  amount?: string;
  category?: string;
  description?: string;
  date?: string;
}

/** Mode présélectionné : le premier actif dans l'ordre d'affichage, « Espèces » (RG-T19). */
export function defaultMode(refs: References): string | null {
  return refs.modes.find((mode) => mode.active)?.id ?? null;
}

export function emptyDraft(refs: References, today: string): Draft {
  return {
    amount: null,
    categoryId: null,
    tags: [],
    description: "",
    locationId: null,
    beneficiary: "",
    modeId: defaultMode(refs),
    date: today,
  };
}

/** « Refaire cette dépense » : montant, catégorie, tags, bénéficiaire, à la date du jour. */
export function repeatedDraft(refs: References, today: string, source: ExpenseDraft): Draft {
  return {
    ...emptyDraft(refs, today),
    amount: source.amount,
    categoryId: source.category_id,
    tags: source.tags.map((tag) => tag.name),
    beneficiary: source.beneficiary ?? "",
    date: source.spent_on,
  };
}

export function draftOf(expense: Expense): Draft {
  return {
    amount: expense.amount,
    categoryId: expense.category_id,
    tags: expense.tags.map((tag) => tag.name),
    description: expense.description ?? "",
    locationId: expense.location_id,
    beneficiary: expense.beneficiary ?? "",
    modeId: expense.payment_mode_id,
    date: expense.spent_on,
  };
}

export function requiresDescription(refs: References, categoryId: string | null): boolean {
  return refs.categories.some((c) => c.id === categoryId && c.requires_description);
}

export function draftProblems(draft: Draft, refs: References, today: string): DraftProblems {
  const problems: DraftProblems = {};
  if (draft.amount === null || draft.amount <= 0) problems.amount = "Le montant est vide";
  if (draft.categoryId === null) problems.category = "Choisissez une catégorie";
  if (requiresDescription(refs, draft.categoryId) && draft.description.trim() === "") {
    problems.description = "La description est obligatoire pour cette catégorie";
  }
  const date = dateProblem(draft.date, today, refs.me.role === "owner");
  if (date !== undefined) problems.date = date;
  return problems;
}

const optional = (text: string) => (text.trim() === "" ? null : text.trim());

function required<T>(value: T | null, name: string): T {
  if (value === null) throw new Error(`Brouillon incomplet : ${name} (contrôle oublié)`);
  return value;
}

/** Corps de `POST /expenses` ; date du jour → omise (le serveur prend sa journée métier). */
export function createBody(draft: Draft, id: string, today: string): ExpenseCreate {
  return {
    id,
    amount: required(draft.amount, "montant"),
    category_id: required(draft.categoryId, "catégorie"),
    spent_on: draft.date === today ? null : draft.date,
    payment_mode_id: draft.modeId,
    tags: [...draft.tags],
    description: optional(draft.description),
    location_id: draft.locationId,
    beneficiary: optional(draft.beneficiary),
  };
}

/** Corps de `PATCH /expenses/{id}` : seuls les champs changés, avec la `version` lue. */
export function patchBody(draft: Draft, expense: Expense): ExpensePatch {
  const before = draftOf(expense);
  const patch: ExpensePatch = { version: expense.version };
  if (draft.amount !== before.amount) patch.amount = required(draft.amount, "montant");
  if (draft.categoryId !== before.categoryId) patch.category_id = draft.categoryId;
  if (draft.date !== before.date) patch.spent_on = draft.date;
  if (draft.modeId !== before.modeId) patch.payment_mode_id = draft.modeId;
  if (draft.tags.join("\n") !== before.tags.join("\n")) patch.tags = [...draft.tags];
  if (draft.description !== before.description) patch.description = optional(draft.description);
  if (draft.locationId !== before.locationId) patch.location_id = draft.locationId;
  if (draft.beneficiary !== before.beneficiary) patch.beneficiary = optional(draft.beneficiary);
  return patch;
}
