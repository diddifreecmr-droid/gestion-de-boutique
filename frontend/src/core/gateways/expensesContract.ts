/**
 * Passerelle des écrans Dépenses (specs § 4.6, § 6.3 « Dépenses ») : l'écran dépend de cette
 * interface, jamais de `fetch`. Tous les types viennent du contrat **généré** (schema.gen.ts).
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type Expense = Schemas["ExpenseResponse"];
export type ExpensePage = Schemas["ExpensePageResponse"];
export type ExpenseCreate = Schemas["ExpenseCreateRequest"];
export type ExpensePatch = Schemas["ExpensePatch"];
export type ExpenseDraft = Schemas["ExpenseDraftResponse"];
export type ExpenseCategory = Schemas["ExpenseCategoryResponse"];
export type ExpenseCategoryPatch = Schemas["ExpenseCategoryPatch"];
export type Tag = Schemas["TagResponse"];
export type TagMergeResult = Schemas["TagMergeResponse"];
export type PaymentMode = Schemas["PaymentModeResponse"];
export type Location = Schemas["LocationResponse"];
export type Member = Schemas["MemberResponse"];

/** Filtres de `GET /expenses` (absents = liste du jour, toutes catégories…). */
export interface ExpenseFilters {
  from?: string;
  to?: string;
  category_id?: string;
  tag_id?: string;
  location_id?: string;
  user_id?: string;
  payment_mode_id?: string;
}

export interface ExpensesGateway {
  list(shopId: string, filters: ExpenseFilters, cursor?: string): Promise<ExpensePage>;
  get(shopId: string, expenseId: string): Promise<Expense>;
  record(shopId: string, body: ExpenseCreate): Promise<Expense>;
  correct(shopId: string, expenseId: string, patch: ExpensePatch): Promise<Expense>;
  cancel(shopId: string, expenseId: string, reason: string): Promise<Expense>;
  /** Brouillon de « Refaire cette dépense » : rien n'est enregistré (UC-DEP-05). */
  repeat(shopId: string, expenseId: string): Promise<ExpenseDraft>;
  categories(shopId: string): Promise<ExpenseCategory[]>;
  createCategory(shopId: string, id: string, name: string): Promise<ExpenseCategory>;
  updateCategory(
    shopId: string,
    categoryId: string,
    patch: ExpenseCategoryPatch,
  ): Promise<ExpenseCategory>;
  tags(shopId: string, search?: string): Promise<Tag[]>;
  mergeTags(shopId: string, sourceId: string, targetId: string): Promise<TagMergeResult>;
  paymentModes(shopId: string): Promise<PaymentMode[]>;
  locations(shopId: string): Promise<Location[]>;
  /** Propriétaire seulement (`MEMBER_MANAGE`) : noms des auteurs. */
  members(shopId: string): Promise<Member[]>;
}
