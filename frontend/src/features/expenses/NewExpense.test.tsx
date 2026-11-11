import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { isUuidV7 } from "../../core/api/uuidv7";
import { axeViolations } from "../../testing/axe";
import {
  EXPENSES_PATH,
  expense,
  expenseRoutes,
  NOW,
  preloadExpenses,
  route,
  setClock,
} from "../../testing/expensesApi";
import { apiError, json, type Call } from "../../testing/fakeApi";
import { renderApp } from "../../testing/renderApp";
import { gestureCounter, plain } from "../../testing/renderSale";
import { ATTACHMENTS_PENDING } from "./ExpenseExtras";
import { FIX_FIELDS } from "./ExpenseForm";
import { OFFLINE_MESSAGE } from "./expenseErrors";

const NEW_PATH = `${EXPENSES_PATH}?vue=nouvelle`;
const POST = route("POST", "/expenses");

beforeAll(preloadExpenses);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const radio = (name: string) => screen.getByRole("radio", { name });
const amount = () => screen.getByLabelText("Montant");
const validate = () => screen.getByRole("button", { name: "Valider la dépense" });
const recorded = (number = "D-000012") =>
  screen.findByRole("heading", { name: `Dépense enregistrée — ${number}` });

function posted(calls: readonly Call[]): unknown {
  const call = calls.find((c) => c.method === "POST" && c.url.endsWith("/expenses"));
  if (call === undefined) throw new Error("Aucune dépense envoyée");
  return call.body;
}

describe("Nouvelle dépense (UC-DEP-01)", () => {
  it("se fait en 3 gestes : montant, catégorie, valider", async () => {
    const { user, fake, container } = renderApp(NEW_PATH, {
      ...expenseRoutes("accountant"),
      [POST]: json(201, expense()),
    });
    const gestures = gestureCounter();
    await screen.findByRole("heading", { name: "Nouvelle dépense" });
    expect(await axeViolations(container)).toEqual([]);

    await gestures.run(() => user.type(amount(), "15000"));
    await gestures.run(() => user.click(radio("Carburant")));
    await gestures.run(() => user.click(validate()));

    expect(await recorded()).toHaveFocus();
    expect(gestures.count).toBe(3);
    const body = posted(fake.calls) as { id: string };
    expect(isUuidV7(body.id)).toBe(true);
    expect(body).toEqual({
      id: body.id,
      amount: 15000,
      category_id: "cat-carburant",
      spent_on: null,
      payment_mode_id: "mode-cash",
      tags: [],
      description: null,
      location_id: null,
      beneficiary: null,
    });
    expect(await axeViolations(container)).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Nouvelle dépense" }));
    expect(amount()).toHaveValue("");
  });

  it("Espèces par défaut, aujourd'hui par défaut, justificatif indisponible avec sa raison", async () => {
    const { user } = renderApp(NEW_PATH, expenseRoutes("accountant"));
    await screen.findByRole("heading", { name: "Nouvelle dépense" });
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    expect(radio("Espèces")).toHaveAttribute("aria-checked", "true");
    const date = screen.getByLabelText("Date");
    expect(date).toHaveValue("2026-11-11");
    expect(date).toHaveAttribute("max", "2026-11-11");
    expect(date).toHaveAttribute("min", "2026-11-04");
    const proof = screen.getByRole("button", { name: "Ajouter le justificatif" });
    expect(proof).toHaveAttribute("aria-disabled", "true");
    expect(proof).toHaveAccessibleDescription(ATTACHMENTS_PENDING);
  });

  it("propriétaire : aucune borne passée (RG-T09)", async () => {
    renderApp(NEW_PATH, expenseRoutes("owner"));
    await screen.findByRole("heading", { name: "Nouvelle dépense" });
    expect(screen.getByLabelText("Date")).not.toHaveAttribute("min");
  });

  it("« Autre » exige une description : signalée, puis envoyée", async () => {
    const { user, fake } = renderApp(NEW_PATH, {
      ...expenseRoutes("accountant"),
      [POST]: json(201, expense({ category_id: "cat-autre", description: "Clés" })),
    });
    await screen.findByRole("heading", { name: "Nouvelle dépense" });
    await user.type(amount(), "2000");
    expect(screen.queryByLabelText(/^Description/)).not.toBeVisible();
    await user.click(radio("Autre"));
    const description = screen.getByRole("textbox", { name: "Description" });
    expect(description).toBeVisible();
    expect(description).toBeRequired();
    await user.click(validate());
    expect(screen.getByText(FIX_FIELDS)).toBeVisible();
    expect(screen.getByText("La description est obligatoire pour cette catégorie")).toBeVisible();
    expect(fake.count(POST)).toBe(0);

    await user.type(description, "Clés");
    await user.click(validate());
    expect(await recorded()).toBeVisible();
    expect(posted(fake.calls)).toMatchObject({ category_id: "cat-autre", description: "Clés" });
  });

  it("tags : suggestion choisie et tag nouveau créé à la volée", async () => {
    const { user, fake } = renderApp(NEW_PATH, {
      ...expenseRoutes("accountant"),
      [route("GET", "/tags?search=g")]: json(200, [{ id: "tag-1", name: "groupe électrogène" }]),
      [route("GET", "/tags?search=f")]: json(200, []),
      [route("GET", "/tags?search=fe")]: json(200, []),
      [POST]: json(201, expense()),
    });
    await screen.findByRole("heading", { name: "Nouvelle dépense" });
    await user.type(amount(), "5000");
    await user.click(radio("Carburant"));
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    const tags = screen.getByLabelText("Tags");
    await user.type(tags, "g");
    const proposed = await screen.findByRole("list", { name: "Tags proposés" });
    await user.click(within(proposed).getByRole("button", { name: "groupe électrogène" }));
    await user.type(tags, "fe");
    await user.click(await screen.findByRole("button", { name: "Créer le tag « fe »" }));
    const chosen = screen.getByRole("list", { name: "Tags choisis" });
    expect(
      within(chosen)
        .getAllByRole("button")
        .map((b) => b.textContent),
    ).toEqual(["groupe électrogène", "fe"]);
    await user.click(validate());
    expect(await recorded()).toBeVisible();
    expect(posted(fake.calls)).toMatchObject({ tags: ["groupe électrogène", "fe"] });
  });

  it("hors connexion : saisie conservée, même identifiant au renvoi (pas de doublon)", async () => {
    const { user, fake } = renderApp(NEW_PATH, {
      ...expenseRoutes("accountant"),
      [POST]: [new TypeError("Failed to fetch"), json(201, expense())],
    });
    await screen.findByRole("heading", { name: "Nouvelle dépense" });
    await user.type(amount(), "15000");
    await user.click(radio("Carburant"));
    await user.click(validate());
    expect(await screen.findByText(OFFLINE_MESSAGE)).toBeVisible();
    expect(plain((amount() as HTMLInputElement).value)).toBe("15 000");
    await user.click(validate());
    expect(await recorded()).toBeVisible();
    const ids = fake.calls
      .filter((c) => `${c.method} ${c.url}` === POST)
      .map((c) => (c.body as { id: string }).id);
    expect(new Set(ids).size).toBe(1);
  });

  it("date refusée par le serveur : message avec les bornes", async () => {
    const { user } = renderApp(NEW_PATH, {
      ...expenseRoutes("accountant"),
      [POST]: apiError(422, "DATE_OUT_OF_RANGE", "Une date dans le futur est refusée", {
        min_date: "2026-11-04",
        max_date: "2026-11-11",
      }),
    });
    await screen.findByRole("heading", { name: "Nouvelle dépense" });
    await user.type(amount(), "15000");
    await user.click(radio("Carburant"));
    await user.click(validate());
    expect(
      await screen.findByText(/choisissez une date du 04\/11\/2026 jusqu'au 11\/11\/2026/),
    ).toBeVisible();
  });
});
