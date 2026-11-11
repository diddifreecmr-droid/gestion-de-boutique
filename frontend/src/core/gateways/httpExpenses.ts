/**
 * Passerelle réelle des Dépenses : routes `/api/v1/shops/{shop_id}/…` (T18), appels
 * authentifiés par `session.authorized` (refresh unique puis rejeu). Rien n'est avalé :
 * `ApiError` et `NetworkError` remontent à l'écran.
 */
import { createContext, useContext } from "react";
import type { AppServices } from "../services/createServices";
import type { ExpenseFilters, ExpensesGateway } from "./expensesContract";

const EXPENSES = "/api/v1/shops/{shop_id}/expenses";
const EXPENSE = "/api/v1/shops/{shop_id}/expenses/{expense_id}";
const CATEGORIES = "/api/v1/shops/{shop_id}/expense-categories";

export function createHttpExpenses({ api, session }: AppServices): ExpensesGateway {
  const shop = (shopId: string) => ({ shop_id: shopId });
  const one = (shopId: string, expenseId: string) => ({ shop_id: shopId, expense_id: expenseId });
  return {
    list: (shopId, filters: ExpenseFilters, cursor) =>
      session.authorized((token) =>
        api.get(EXPENSES, { token, params: shop(shopId), query: { ...filters, cursor } }),
      ),
    get: (shopId, expenseId) =>
      session.authorized((token) => api.get(EXPENSE, { token, params: one(shopId, expenseId) })),
    record: (shopId, body) =>
      session.authorized((token) => api.post(EXPENSES, { token, params: shop(shopId), body })),
    correct: (shopId, expenseId, patch) =>
      session.authorized((token) =>
        api.patch(EXPENSE, { token, params: one(shopId, expenseId), body: patch }),
      ),
    cancel: (shopId, expenseId, reason) =>
      session.authorized((token) =>
        api.post(`${EXPENSE}/cancel`, {
          token,
          params: one(shopId, expenseId),
          body: { reason },
        }),
      ),
    repeat: (shopId, expenseId) =>
      session.authorized((token) =>
        api.get(`${EXPENSE}/repeat`, { token, params: one(shopId, expenseId) }),
      ),
    categories: (shopId) =>
      session.authorized((token) => api.get(CATEGORIES, { token, params: shop(shopId) })),
    createCategory: (shopId, id, name) =>
      session.authorized((token) =>
        api.post(CATEGORIES, { token, params: shop(shopId), body: { id, name } }),
      ),
    updateCategory: (shopId, categoryId, patch) =>
      session.authorized((token) =>
        api.patch(`${CATEGORIES}/{category_id}`, {
          token,
          params: { shop_id: shopId, category_id: categoryId },
          body: patch,
        }),
      ),
    tags: (shopId, search) =>
      session.authorized((token) =>
        api.get("/api/v1/shops/{shop_id}/tags", {
          token,
          params: shop(shopId),
          query: { search: search === "" ? undefined : search },
        }),
      ),
    mergeTags: (shopId, sourceId, targetId) =>
      session.authorized((token) =>
        api.post("/api/v1/shops/{shop_id}/tags/merge", {
          token,
          params: shop(shopId),
          body: { source_id: sourceId, target_id: targetId },
        }),
      ),
    paymentModes: (shopId) =>
      session.authorized((token) =>
        api.get("/api/v1/shops/{shop_id}/payment-modes", { token, params: shop(shopId) }),
      ),
    locations: async (shopId) => {
      const found = await session.authorized((token) =>
        api.get("/api/v1/shops/{shop_id}/locations", { token, params: shop(shopId) }),
      );
      return found.items;
    },
    members: (shopId) =>
      session.authorized((token) =>
        api.get("/api/v1/shops/{shop_id}/members", { token, params: shop(shopId) }),
      ),
  };
}

/** Passerelle et horloge des écrans Dépenses (l'horloge est remplacée dans les tests). */
export interface ExpensesDeps {
  gateway: ExpensesGateway;
  now: () => Date;
}

export const ExpensesContext = createContext<ExpensesDeps | null>(null);

/** Hors d'un fournisseur, c'est une erreur de câblage (fail-fast). */
export function useExpensesDeps(): ExpensesDeps {
  const deps = useContext(ExpensesContext);
  if (deps === null) throw new Error("useExpensesDeps doit être appelé sous ExpensesContext");
  return deps;
}
