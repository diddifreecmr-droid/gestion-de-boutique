import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { isUuidV7 } from "../../core/api/uuidv7";
import { axeViolations } from "../../testing/axe";
import { setClock } from "../../testing/expensesApi";
import { apiError, json } from "../../testing/fakeApi";
import {
  DETAIL_PATH,
  GET_ONE,
  NOW,
  preloadReceivables,
  receivable,
  receivableRoutes,
  RECEIVABLE_ID,
  route,
} from "../../testing/receivables";
import { renderApp } from "../../testing/renderApp";
import { ATTACHMENTS_PENDING } from "./GuarantorsSection";

const ADD_REMINDER = route("POST", `/receivables/${RECEIVABLE_ID}/reminders`);
const PATCH_REMINDER = route("PATCH", "/reminders/rem-1");
const ADD_GUARANTOR = route("POST", `/receivables/${RECEIVABLE_ID}/guarantors`);

const reminder = (overrides = {}) => ({
  id: "rem-1",
  remind_on: "2026-11-30",
  note: "Il a promis 200 000 fin du mois",
  status: "upcoming",
  alerted_for: null,
  ...overrides,
});

beforeAll(preloadReceivables);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const reminders = () => within(screen.getByRole("region", { name: "Rappels" }));
const heading = () => screen.findByRole("heading", { name: "Créance de Moussa Hamadou" });

describe("Rappels (UC-CRE-06)", () => {
  it("vendeur : programmer, marquer fait, reporter ; rappel dépassé signalé", async () => {
    const { user, fake, container } = renderApp(DETAIL_PATH, {
      ...receivableRoutes("seller"),
      [GET_ONE]: json(200, receivable({ reminders: [reminder({ remind_on: "2026-11-01" })] })),
      [ADD_REMINDER]: json(201, receivable({ reminders: [reminder()] })),
      [PATCH_REMINDER]: [
        json(
          200,
          receivable({ reminders: [reminder({ status: "postponed", remind_on: "2026-12-05" })] }),
        ),
        json(
          200,
          receivable({ reminders: [reminder({ status: "done", remind_on: "2026-12-05" })] }),
        ),
      ],
    });
    await heading();
    expect(reminders().getByText("Dépassé")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);

    await user.click(reminders().getByRole("button", { name: "Programmer le rappel" }));
    expect(reminders().getByText("Choisissez la date du rappel")).toBeVisible();
    expect(fake.count(ADD_REMINDER)).toBe(0);
    await user.type(reminders().getByLabelText("Date du rappel"), "2026-11-30");
    await user.type(
      reminders().getByLabelText("Note (facultatif)"),
      "Il a promis 200 000 fin du mois",
    );
    await user.click(reminders().getByRole("button", { name: "Programmer le rappel" }));
    expect(await reminders().findByText("À venir")).toBeVisible();
    const sent = fake.calls.find((c) => `${c.method} ${c.url}` === ADD_REMINDER)?.body as {
      id: string;
    };
    expect(isUuidV7(sent.id)).toBe(true);
    expect(sent).toEqual({
      id: sent.id,
      remind_on: "2026-11-30",
      note: "Il a promis 200 000 fin du mois",
    });

    await user.click(reminders().getByRole("button", { name: "Reporter" }));
    await user.click(reminders().getByRole("button", { name: "Reporter le rappel" }));
    expect(reminders().getByText("Choisissez la nouvelle date")).toBeVisible();
    await user.type(reminders().getByLabelText("Nouvelle date du rappel"), "2026-12-05");
    await user.click(reminders().getByRole("button", { name: "Reporter le rappel" }));
    expect(await reminders().findByText("Reporté")).toBeVisible();
    expect(reminders().getByText("Le 05/12/2026")).toBeVisible();

    await user.click(reminders().getByRole("button", { name: "Marquer fait" }));
    expect(await reminders().findByText("Fait")).toBeVisible();
    expect(reminders().queryByRole("button", { name: "Marquer fait" })).toBeNull();
    expect(fake.calls.filter((c) => c.method === "PATCH").map((c) => c.body)).toEqual([
      { status: "postponed", remind_on: "2026-12-05" },
      { status: "done" },
    ]);
  });

  it("refus INVALID_STATE_TRANSITION : message clair, la fiche reste", async () => {
    const { user } = renderApp(DETAIL_PATH, {
      ...receivableRoutes("owner"),
      [GET_ONE]: json(200, receivable({ reminders: [reminder()] })),
      [PATCH_REMINDER]: apiError(422, "INVALID_STATE_TRANSITION", "Ce rappel est déjà fait"),
    });
    await heading();
    await user.click(reminders().getByRole("button", { name: "Marquer fait" }));
    expect(
      await screen.findByText("Action impossible dans l'état actuel : Ce rappel est déjà fait."),
    ).toBeVisible();
  });
});

describe("Garants (UC-CRE-07)", () => {
  it("nom, téléphone, lien ; pièce d'identité désactivée avec sa raison", async () => {
    const guarantor = { id: "g-1", name: "Ali Bouba", phone: "+237690000009", relation: "frère" };
    const { user, fake } = renderApp(DETAIL_PATH, {
      ...receivableRoutes("seller"),
      [GET_ONE]: json(200, receivable()),
      [ADD_GUARANTOR]: json(201, receivable({ guarantors: [guarantor] })),
    });
    await heading();
    const section = within(screen.getByRole("region", { name: "Garants" }));
    expect(section.getByText("Aucun garant.")).toBeVisible();
    const idDoc = section.getByRole("button", { name: "Pièce d'identité" });
    expect(idDoc).toHaveAttribute("aria-disabled", "true");
    expect(section.getByText(ATTACHMENTS_PENDING)).toBeVisible();

    await user.click(section.getByRole("button", { name: "Ajouter le garant" }));
    expect(section.getByText("Le nom est vide")).toBeVisible();
    expect(section.getByText("Le téléphone doit avoir 9 chiffres")).toBeVisible();
    await user.type(section.getByLabelText("Nom du garant"), "Ali Bouba");
    await user.type(section.getByLabelText("Téléphone du garant"), "6 90 00 00 09");
    await user.type(section.getByLabelText("Lien avec le client (facultatif)"), "frère");
    await user.click(section.getByRole("button", { name: "Ajouter le garant" }));
    expect(await section.findByText("Ali Bouba")).toBeVisible();
    expect(section.getByText("+237690000009 · frère")).toBeVisible();
    const sent = fake.calls.find((c) => `${c.method} ${c.url}` === ADD_GUARANTOR)?.body as {
      id: string;
    };
    expect(sent).toEqual({
      id: sent.id,
      name: "Ali Bouba",
      phone: "+237690000009",
      relation: "frère",
    });
    expect(section.getByLabelText("Nom du garant")).toHaveValue("");
  });
});
