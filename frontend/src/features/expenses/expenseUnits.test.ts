import { describe, expect, it } from "vitest";
import { ApiError, NetworkError } from "../../core/api/errors";
import {
  ACCOUNTANT_ID,
  CATEGORIES,
  DEADLINE,
  expense,
  MODES,
  OWNER_ID,
} from "../../testing/expensesApi";
import { barWidth } from "./barWidth";
import { addDays, businessDate, dateBounds, dateProblem, monthStart } from "./businessDay";
import { AFTER_MIDNIGHT, ALREADY_CANCELLED, correctionOf, NOT_AUTHOR } from "./correctionRule";
import { createBody, draftOf, emptyDraft, patchBody } from "./draft";
import { expenseErrorMessage, OFFLINE_MESSAGE } from "./expenseErrors";
import { defaultFilters, periodProblem, toQuery } from "./filters";
import type { References } from "./references";

const refs = (role: "owner" | "accountant"): References => ({
  categories: CATEGORIES,
  modes: [...MODES].sort((a, b) => a.display_order - b.display_order),
  locations: [],
  members: new Map(),
  me: { userId: role === "owner" ? OWNER_ID : ACCOUNTANT_ID, name: "X", role },
});

describe("jour métier à Douala", () => {
  it("minuit à Douala = 23:00 UTC la veille", () => {
    expect(businessDate(new Date("2026-11-11T22:59:59Z"))).toBe("2026-11-11");
    expect(businessDate(new Date("2026-11-11T23:00:00Z"))).toBe("2026-11-12");
    expect(() => businessDate(new Date("x"))).toThrow("instant invalide");
  });

  it("bornes RG-T09 : J-7 accepté, J-8 refusé, futur refusé ; propriétaire sans borne passée", () => {
    expect(addDays("2026-03-01", -1)).toBe("2026-02-28");
    expect(monthStart("2026-11-11")).toBe("2026-11-01");
    expect(() => addDays("bad", 1)).toThrow("date invalide");
    expect(dateBounds("2026-11-11", true)).toEqual({ max: "2026-11-11" });
    expect(dateProblem("2026-11-04", "2026-11-11", false)).toBeUndefined();
    expect(dateProblem("2026-11-03", "2026-11-11", false)).toMatch(/7 jours/);
    expect(dateProblem("2026-11-12", "2026-11-11", true)).toMatch(/futur/);
    expect(dateProblem("2020-01-01", "2026-11-11", true)).toBeUndefined();
    expect(dateProblem("", "2026-11-11", true)).toBe("La date est vide");
  });
});

describe("délai de correction (UC-DEP-04)", () => {
  const before = new Date("2026-11-11T22:59:00Z");
  const after = new Date(DEADLINE);
  it("comptable : ses dépenses, jusqu'à minuit exclu", () => {
    expect(correctionOf(expense(), "accountant", ACCOUNTANT_ID, before)).toEqual({ allowed: true });
    expect(correctionOf(expense(), "accountant", ACCOUNTANT_ID, after)).toEqual({
      allowed: false,
      reason: AFTER_MIDNIGHT,
    });
    expect(
      correctionOf(expense({ created_by: OWNER_ID }), "accountant", ACCOUNTANT_ID, before),
    ).toEqual({ allowed: false, reason: NOT_AUTHOR });
    expect(() =>
      correctionOf(expense({ correction_deadline: "?" }), "accountant", ACCOUNTANT_ID, before),
    ).toThrow("illisible");
  });
  it("propriétaire : toujours, tant que la dépense est valide", () => {
    expect(correctionOf(expense(), "owner", OWNER_ID, after)).toEqual({ allowed: true });
    expect(correctionOf(expense({ status: "cancelled" }), "owner", OWNER_ID, after)).toEqual({
      allowed: false,
      reason: ALREADY_CANCELLED,
    });
    expect(correctionOf(expense({ editable: false }), "owner", OWNER_ID, after).allowed).toBe(
      false,
    );
  });
});

describe("brouillon et corps envoyés", () => {
  it("création : date du jour omise, textes vides → null ; correction : champs changés seulement", () => {
    const draft = {
      ...emptyDraft(refs("owner"), "2026-11-11"),
      amount: 100,
      categoryId: "cat-repas",
      description: "  ",
    };
    expect(draft.modeId).toBe("mode-cash");
    expect(createBody(draft, "id-1", "2026-11-11")).toMatchObject({
      spent_on: null,
      description: null,
    });
    expect(createBody({ ...draft, date: "2026-11-10" }, "id-1", "2026-11-11").spent_on).toBe(
      "2026-11-10",
    );
    expect(() => createBody({ ...draft, amount: null }, "id", "2026-11-11")).toThrow("montant");
    const source = expense({ version: 7, tags: [{ id: "t", name: "a" }] });
    const changed = {
      ...draftOf(source),
      tags: ["a", "b"],
      description: "x",
      beneficiary: "y",
      locationId: "l",
      modeId: "m",
      date: "2026-11-10",
      categoryId: "c",
    };
    expect(patchBody(changed, source)).toEqual({
      version: 7,
      tags: ["a", "b"],
      description: "x",
      beneficiary: "y",
      location_id: "l",
      payment_mode_id: "m",
      spent_on: "2026-11-10",
      category_id: "c",
    });
  });
});

describe("filtres, barres, messages", () => {
  it("période : mois, dates choisies, période incomplète ou inversée", () => {
    const base = defaultFilters("2026-11-11");
    expect(toQuery(base, "2026-11-11")).toEqual({});
    expect(
      toQuery(
        { ...base, period: "month", modeId: "m", locationId: "l", tag: { id: "t", name: "t" } },
        "2026-11-11",
      ),
    ).toEqual({
      from: "2026-11-01",
      to: "2026-11-11",
      payment_mode_id: "m",
      location_id: "l",
      tag_id: "t",
    });
    expect(periodProblem({ ...base, period: "custom", from: "" })).toBe(
      "Choisissez les deux dates",
    );
    expect(periodProblem({ ...base, period: "custom", from: "2026-11-12" })).toMatch(/après/);
    expect(() => toQuery({ ...base, period: "custom", to: "" }, "2026-11-11")).toThrow(
      "incomplète",
    );
  });

  it("largeur des barres par pas de 5 %, part non nulle toujours visible", () => {
    expect(barWidth(0, 10)).toBe("w-0");
    expect(barWidth(1, 1000)).toBe("w-1/20");
    expect(barWidth(10, 10)).toBe("w-full");
    expect(() => barWidth(11, 10)).toThrow("incohérente");
  });

  it("messages d'erreur ; une erreur imprévue est relancée", () => {
    const api = (code: string, details = {}) => new ApiError(422, code, "m", details);
    expect(expenseErrorMessage(new NetworkError("x"))).toBe(OFFLINE_MESSAGE);
    for (const code of [
      "INACTIVE_REFERENCE",
      "REASON_REQUIRED",
      "DESCRIPTION_REQUIRED",
      "INVALID_TAG_MERGE",
      "FORBIDDEN",
      "AUTRE",
    ]) {
      expect(expenseErrorMessage(api(code))).not.toBe("");
    }
    expect(expenseErrorMessage(api("DATE_OUT_OF_RANGE"))).toBe("m");
    expect(() => expenseErrorMessage(api("CORRECTION_WINDOW_CLOSED"))).toThrow("heure limite");
    expect(() => expenseErrorMessage(new TypeError("bug"))).toThrow("bug");
  });
});
