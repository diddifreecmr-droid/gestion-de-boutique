import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../testing/axe";
import {
  ACCOUNTANT_ID,
  DEADLINE,
  EXPENSES_PATH,
  expense,
  expenseRoutes,
  NOW,
  preloadExpenses,
  OWNER_ID,
  route,
  setClock,
} from "../../testing/expensesApi";
import { apiError, json } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { plain } from "../../testing/renderSale";
import { AFTER_MIDNIGHT, NOT_AUTHOR } from "./correctionRule";

const DETAIL = `${EXPENSES_PATH}?vue=fiche&id=exp-12`;
const GET = route("GET", "/expenses/exp-12");
const CANCEL = route("POST", "/expenses/exp-12/cancel");
const PATCH = route("PATCH", "/expenses/exp-12");

beforeAll(preloadExpenses);
beforeEach(() => {
  window.localStorage.clear();
});
afterEach(() => {
  vi.useRealTimers();
});

const button = (name: string) => screen.getByRole("button", { name });
const heading = () => screen.findByRole("heading", { name: "Dépense D-000012" });

describe("Fiche dépense (UC-DEP-04, UC-DEP-05)", () => {
  it("comptable avant minuit : annuler exige un motif, puis la dépense reste visible barrée", async () => {
    setClock("2026-11-11T22:59:00Z"); // 23 h 59 à Douala
    const cancelled = expense({
      status: "cancelled",
      editable: false,
      cancellation: {
        cancelled_at: "2026-11-11T22:59:00Z",
        cancelled_by: ACCOUNTANT_ID,
        reason: "erreur",
      },
    });
    const { user, fake, container } = renderApp(DETAIL, {
      ...expenseRoutes("accountant"),
      [GET]: json(200, expense()),
      [CANCEL]: json(200, cancelled),
    });
    await heading();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(button("Annuler la dépense"));
    const dialog = screen.getByRole("dialog", { name: "Annuler la dépense D-000012 ?" });
    await user.click(within(dialog).getByRole("button", { name: "Annuler la dépense" }));
    expect(within(dialog).getByText("Le motif est obligatoire")).toBeVisible();
    expect(fake.count(CANCEL)).toBe(0);

    await user.type(within(dialog).getByLabelText("Motif"), "  erreur ");
    await user.click(within(dialog).getByRole("button", { name: "Annuler la dépense" }));
    expect(
      await screen.findByText("Annulée le 11/11/2026 à 23 h 59 par Paul Ndam — motif : erreur", {
        normalizer: plain,
      }),
    ).toBeVisible();
    expect(fake.calls.find((c) => `${c.method} ${c.url}` === CANCEL)?.body).toEqual({
      reason: "erreur",
    });
    expect(screen.queryByRole("button", { name: "Modifier" })).toBeNull();
    expect(button("Refaire cette dépense")).toBeVisible();
  });

  it("comptable après minuit : actions indisponibles avec la raison, même si la fiche dit « editable »", async () => {
    setClock("2026-11-11T23:00:00Z"); // minuit pile à Douala : délai clos
    renderApp(DETAIL, { ...expenseRoutes("accountant"), [GET]: json(200, expense()) });
    await heading();
    for (const name of ["Modifier", "Annuler la dépense"]) {
      expect(button(name)).toHaveAttribute("aria-disabled", "true");
      expect(button(name)).toHaveAccessibleDescription(AFTER_MIDNIGHT);
    }
  });

  it("comptable : la dépense d'un autre membre ne se corrige pas", async () => {
    setClock(NOW);
    renderApp(DETAIL, {
      ...expenseRoutes("accountant"),
      [GET]: json(200, expense({ created_by: OWNER_ID, editable: false })),
    });
    await heading();
    expect(button("Modifier")).toHaveAccessibleDescription(NOT_AUTHOR);
    expect(screen.getByText(/par un autre membre/)).toBeVisible();
  });

  it("CORRECTION_WINDOW_CLOSED renvoyé quand même : message avec l'heure limite", async () => {
    setClock(NOW);
    const { user } = renderApp(DETAIL, {
      ...expenseRoutes("accountant"),
      [GET]: json(200, expense()),
      [CANCEL]: apiError(422, "CORRECTION_WINDOW_CLOSED", "Délai dépassé", { deadline: DEADLINE }),
    });
    await heading();
    await user.click(button("Annuler la dépense"));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("Motif"), "erreur");
    await user.click(within(dialog).getByRole("button", { name: "Annuler la dépense" }));
    expect(
      await screen.findByText(
        "Délai dépassé (heure limite : 12/11/2026 à 00 h 00) : seul le propriétaire peut encore modifier cette dépense.",
        { normalizer: plain },
      ),
    ).toBeVisible();
  });

  it("propriétaire : corrige avec la version lue, seuls les champs changés partent", async () => {
    setClock("2026-11-13T08:00:00Z");
    const { user, fake } = renderApp(DETAIL, {
      ...expenseRoutes("owner"),
      [GET]: json(200, expense({ version: 3 })),
      [PATCH]: json(200, expense({ amount: 17000, version: 4 })),
    });
    await heading();
    await user.click(button("Modifier"));
    const amount = await screen.findByLabelText("Montant");
    await user.type(amount, "17000", { initialSelectionStart: 0, initialSelectionEnd: 20 });
    await user.click(button("Enregistrer la correction"));
    await heading();
    expect(fake.calls.find((c) => `${c.method} ${c.url}` === PATCH)?.body).toEqual({
      version: 3,
      amount: 17000,
    });
  });

  it("VERSION_CONFLICT : la correction n'écrase rien et le dit", async () => {
    setClock(NOW);
    const { user } = renderApp(`${EXPENSES_PATH}?vue=modifier&id=exp-12`, {
      ...expenseRoutes("owner"),
      [GET]: json(200, expense()),
      [PATCH]: apiError(409, "VERSION_CONFLICT", "Conflit"),
    });
    const amount = await screen.findByLabelText("Montant");
    await user.type(amount, "1", { initialSelectionStart: 0, initialSelectionEnd: 20 });
    await user.click(button("Enregistrer la correction"));
    expect(await screen.findByText(/modifié cet élément entre-temps/)).toBeVisible();
  });

  it("« Refaire cette dépense » ouvre le formulaire pré-rempli sans rien créer", async () => {
    setClock(NOW);
    const { user, fake } = renderApp(DETAIL, {
      ...expenseRoutes("owner"),
      [GET]: json(200, expense()),
      [route("GET", "/expenses/exp-12/repeat")]: json(200, {
        spent_on: "2026-11-11",
        amount: 50000,
        category_id: "cat-loyer",
        tags: [{ id: "t1", name: "loyer boutique" }],
        beneficiary: "M. Oumarou",
      }),
    });
    await heading();
    await user.click(button("Refaire cette dépense"));
    expect(await screen.findByRole("heading", { name: "Nouvelle dépense" })).toBeVisible();
    expect(plain(screen.getByLabelText<HTMLInputElement>("Montant").value)).toBe("50 000");
    expect(screen.getByRole("radio", { name: "Loyer" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByLabelText("Bénéficiaire")).toHaveValue("M. Oumarou");
    expect(screen.getByRole("list", { name: "Tags choisis" })).toHaveTextContent("loyer boutique");
    expect(fake.count(route("POST", "/expenses"))).toBe(0);
  });
});
