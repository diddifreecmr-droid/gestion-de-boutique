import { screen, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { apiError, json } from "../../testing/fakeApi";
import {
  DETAIL_PATH,
  GET_ONE,
  installment,
  OTHER_SELLER_ID,
  OWNER_ID,
  preloadReceivables,
  receivable,
  receivableRoutes,
  RECEIVABLE_ID,
  route,
} from "../../testing/receivables";
import { renderApp } from "../../testing/renderApp";
import { money, plain } from "../../testing/renderSale";

beforeAll(preloadReceivables);
beforeEach(() => {
  window.localStorage.clear();
});

const heading = () => screen.findByRole("heading", { name: "Créance de Moussa Hamadou" });
const button = (name: string) => screen.getByRole("button", { name });
const CANCELLED = installment({
  id: "inst-0",
  number: "R-000000",
  status: "cancelled",
  cancelled_at: "2026-11-02T13:32:00Z",
  cancelled_by: OWNER_ID,
  cancel_reason: "doublon",
});
const SETTLED = receivable({
  total_paid: 800000,
  remaining: 0,
  status: "settled",
  manageable: true,
  installments: [installment(), installment({ id: "inst-2", number: "R-000002", amount: 600000 })],
});

describe("Fiche créance", () => {
  it("vendeur : faits, versement annulé barré avec motif, aucune action du propriétaire", async () => {
    const { container } = renderApp(DETAIL_PATH, {
      ...receivableRoutes("seller"),
      [GET_ONE]: json(200, receivable({ installments: [CANCELLED, installment()] })),
    });
    await heading();
    expect(screen.getByText("En cours")).toBeVisible();
    expect(screen.getByText("Reste à payer").nextElementSibling).toHaveClass("text-credit-text");
    expect(screen.getByText("Vendeur responsable").nextElementSibling?.textContent).toBe("vous");
    expect(
      plain(screen.getByText("Acompte à la vente").nextElementSibling?.textContent ?? ""),
    ).toBe(money(200000));
    const struck = screen.getByText(/R-000000/);
    expect(struck).toHaveClass("line-through");
    expect(
      screen.getByText("Annulé le 02/11/2026 à 14 h 32 par un autre membre — motif : doublon", {
        normalizer: plain,
      }),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: /Annuler R-/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Passer en perte" })).toBeNull();
    expect(screen.queryByRole("radiogroup", { name: "Vendeur responsable" })).toBeNull();
    expect(button("Enregistrer un versement")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("propriétaire : annuler un versement d'une créance soldée la remet « En cours »", async () => {
    const CANCEL = route("POST", "/installments/inst-2/cancel");
    const reopened = receivable({
      manageable: true,
      installments: [
        installment(),
        { ...CANCELLED, id: "inst-2", number: "R-000002", amount: 600000 },
      ],
    });
    const { user, fake } = renderApp(DETAIL_PATH, {
      ...receivableRoutes("owner"),
      [GET_ONE]: json(200, SETTLED),
      [CANCEL]: json(200, { installment: CANCELLED, receivable: reopened }),
    });
    await heading();
    expect(screen.getByText("Soldée")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Enregistrer un versement" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Passer en perte" })).toBeNull();
    await user.click(button("Annuler R-000002"));
    const dialog = screen.getByRole("dialog", { name: "Annuler le versement R-000002 ?" });
    await user.click(within(dialog).getByRole("button", { name: "Annuler le versement" }));
    expect(within(dialog).getByText("Le motif est obligatoire")).toBeVisible();
    await user.type(within(dialog).getByLabelText("Motif"), "erreur de saisie");
    await user.click(within(dialog).getByRole("button", { name: "Annuler le versement" }));
    expect(await screen.findByText("En cours")).toBeVisible();
    expect(fake.calls.find((c) => c.url.endsWith("/inst-2/cancel"))?.body).toEqual({
      reason: "erreur de saisie",
    });
    expect(button("Enregistrer un versement")).toBeVisible();
  });

  it("propriétaire : passer en perte avec motif, puis un versement reste possible", async () => {
    const WRITE_OFF = route("POST", `/receivables/${RECEIVABLE_ID}/write-off`);
    const lost = receivable({
      manageable: true,
      status: "written_off",
      write_off: { on: "2026-11-11", reason: "client parti", by: OWNER_ID },
    });
    const { user, router } = renderApp(DETAIL_PATH, {
      ...receivableRoutes("owner"),
      [GET_ONE]: json(200, receivable({ manageable: true })),
      [WRITE_OFF]: json(200, lost),
    });
    await heading();
    await user.click(button("Passer en perte"));
    const dialog = screen.getByRole("dialog", {
      name: "Passer en perte la créance de Moussa Hamadou ?",
    });
    expect(plain(dialog.textContent)).toContain(`${money(600000)} sortent du total à recevoir`);
    await user.type(within(dialog).getByLabelText("Motif"), "client parti");
    await user.click(within(dialog).getByRole("button", { name: "Passer en perte" }));
    expect(await screen.findByText("En perte")).toBeVisible();
    expect(
      screen.getByText("Passée en perte le 11/11/2026 par vous — motif : client parti"),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: "Passer en perte" })).toBeNull();
    await user.click(button("Enregistrer un versement"));
    expect(router.state.location.search).toBe(`?vue=versement&id=${RECEIVABLE_ID}`);
  });

  it("propriétaire : changer le vendeur responsable (PATCH avec version), conflit annoncé", async () => {
    const PATCH = route("PATCH", `/receivables/${RECEIVABLE_ID}`);
    const { user, fake } = renderApp(DETAIL_PATH, {
      ...receivableRoutes("owner"),
      [GET_ONE]: json(200, receivable({ manageable: true })),
      [PATCH]: [
        apiError(409, "VERSION_CONFLICT", "Version périmée"),
        json(
          200,
          receivable({ manageable: true, version: 2, responsible_seller_id: OTHER_SELLER_ID }),
        ),
      ],
    });
    await heading();
    expect(
      screen.getByText("Vendeur responsable", { selector: "dt" }).nextElementSibling?.textContent,
    ).toBe("Ibrahim Sali");
    await user.click(screen.getByRole("radio", { name: "Paul Ndam" }));
    await user.click(button("Changer le vendeur responsable"));
    expect(await screen.findByText(/Quelqu'un a modifié cette créance/)).toBeVisible();
    await user.click(button("Changer le vendeur responsable"));
    expect(await screen.findByText("Paul Ndam", { selector: "dd" })).toBeVisible();
    expect(fake.calls.filter((c) => c.method === "PATCH").at(-1)?.body).toEqual({
      version: 1,
      responsible_seller_id: OTHER_SELLER_ID,
    });
  });

  it("hors connexion : la fiche le dit", async () => {
    renderApp(DETAIL_PATH, {
      ...receivableRoutes("seller"),
      [GET_ONE]: new TypeError("Failed to fetch"),
    });
    expect(await screen.findByText("Connexion nécessaire pour afficher cet écran.")).toBeVisible();
  });
});
