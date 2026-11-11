import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { isUuidV7 } from "../../core/api/uuidv7";
import { formatMoney } from "../../shared/format";
import { axeViolations } from "../../testing/axe";
import { json } from "../../testing/fakeApi";
import {
  HAOJUE_ID,
  NOW,
  preloadPurchasing,
  purchase,
  PURCHASES_PATH,
  purchasingRoutes,
  route,
  setClock,
  withArticleSearch,
} from "../../testing/purchasing";
import { chooseArticle, fillLine, lineGroup, sent, summaryValue } from "../../testing/purchasingUi";
import { renderApp } from "../../testing/renderApp";
import { money } from "../../testing/renderSale";
import { FIX_FIELDS } from "./PurchaseForm";
import { ATTACHMENTS_PENDING } from "./PurchaseExtras";

const NEW_PATH = `${PURCHASES_PATH}?vue=nouvel`;
const POST = route("POST", "/purchases");

beforeAll(preloadPurchasing);
beforeEach(() => {
  window.localStorage.clear();
  setClock(NOW);
});
afterEach(() => {
  vi.useRealTimers();
});

const validate = () => screen.getByRole("button", { name: "Valider l'achat" });

describe("Nouvel achat sur un seul écran (UC-ACH-01)", () => {
  it("une ligne + douane : total aussitôt, coût final 540 000 FCFA (CDC § 17.5), puis confirmation", async () => {
    const { user, fake, container } = renderApp(
      NEW_PATH,
      withArticleSearch(purchasingRoutes("accountant", { [POST]: json(201, purchase()) })),
    );
    await screen.findByRole("heading", { name: "Nouvel achat" });
    expect(await axeViolations(container)).toEqual([]);
    expect(screen.getByLabelText("Date de l'achat")).toHaveValue("2026-11-11");
    expect(screen.getByLabelText("Date de l'achat")).toHaveAttribute("min", "2026-11-04");
    expect(screen.getByRole("radio", { name: "Lieu de réception habituel" })).toHaveAttribute(
      "aria-checked",
      "true",
    );

    await chooseArticle(user, "hao", "Haojue HJ125-8");
    await fillLine(user, "20", "520000");
    expect(lineGroup(1)).toHaveTextContent(`Total de la ligne${money(10400000)}`);

    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    await user.click(screen.getByRole("button", { name: "Ajouter : Douane" }));
    await user.type(screen.getByLabelText("Frais : Douane"), "400000");
    expect(summaryValue("Total marchandise")).toBe(formatMoney(10400000));
    expect(summaryValue("Total des frais")).toBe(formatMoney(400000));
    expect(summaryValue("Coût unitaire final — Haojue HJ125-8")).toBe(
      `${formatMoney(540000)} par unité`,
    );
    expect(await axeViolations(container)).toEqual([]);

    await user.click(validate());
    expect(
      await screen.findByRole("heading", { name: "Achat enregistré — A-000012" }),
    ).toHaveFocus();
    const body = sent(fake.calls, "POST", "/purchases") as { id: string };
    expect(isUuidV7(body.id)).toBe(true);
    expect(body).toEqual({
      id: body.id,
      lines: [{ article_id: HAOJUE_ID, quantity: "20", unit: "UNIT", unit_price: 520000 }],
      fees: [{ kind: "customs", amount: 400000, label: null }],
      purchase_date: null,
      location_id: null,
      supplier_id: null,
      invoice_ref: null,
      note: null,
      confirm_price_gap: false,
    });
    await user.click(screen.getByRole("button", { name: "Nouvel achat" }));
    expect(await screen.findByRole("heading", { name: "Nouvel achat" })).toBeVisible();
  });

  it("rien n'est envoyé tant qu'un champ manque ; photo indisponible avec sa raison", async () => {
    const { user, fake } = renderApp(NEW_PATH, withArticleSearch(purchasingRoutes("accountant")));
    await screen.findByRole("heading", { name: "Nouvel achat" });
    await user.click(validate());
    expect(screen.getByText(FIX_FIELDS)).toBeVisible();
    expect(screen.getByText("Choisissez l'article")).toBeVisible();
    await chooseArticle(user, "hao", "Haojue HJ125-8");
    await user.type(within(lineGroup(1)).getByLabelText("Quantité"), "1,5");
    await user.click(validate());
    expect(screen.getByText("Cette unité se compte en nombre entier")).toBeVisible();
    expect(screen.getByText("Le prix unitaire est vide")).toBeVisible();
    expect(fake.count(POST)).toBe(0);
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    const photo = screen.getByRole("button", { name: "Photo de la facture" });
    expect(photo).toHaveAttribute("aria-disabled", "true");
    expect(photo).toHaveAccessibleDescription(ATTACHMENTS_PENDING);
  });

  it("propriétaire : lieu des réglages présélectionné, aucune borne passée, facture et note", async () => {
    const { user, fake } = renderApp(
      NEW_PATH,
      withArticleSearch(purchasingRoutes("owner", { [POST]: json(201, purchase()) })),
    );
    await screen.findByRole("heading", { name: "Nouvel achat" });
    expect(screen.getByRole("radio", { name: "Garoua-Boulaï" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.queryByRole("radio", { name: "Lieu de réception habituel" })).toBeNull();
    const date = screen.getByLabelText("Date de l'achat");
    expect(date).not.toHaveAttribute("min");
    await user.clear(date);
    await user.type(date, "2026-10-01");
    await user.click(screen.getByRole("radio", { name: "Garoua" }));
    await chooseArticle(user, "hao", "Haojue HJ125-8");
    await fillLine(user, "2", "500000");
    await user.click(screen.getByRole("button", { name: "Plus de détails" }));
    await user.type(screen.getByLabelText("Numéro de facture du fournisseur"), "F-77");
    await user.type(screen.getByLabelText("Note"), "Lot de novembre");
    await user.click(validate());
    await screen.findByRole("heading", { name: "Achat enregistré — A-000012" });
    expect(sent(fake.calls, "POST", "/purchases")).toMatchObject({
      purchase_date: "2026-10-01",
      location_id: "loc-garoua",
      invoice_ref: "F-77",
      note: "Lot de novembre",
    });
  });

  it("360 px : aucun conteneur qui élargit la page, retour à la liste", async () => {
    const { user, container, router } = renderApp(
      NEW_PATH,
      withArticleSearch(purchasingRoutes("accountant")),
    );
    await screen.findByRole("heading", { name: "Nouvel achat" });
    await chooseArticle(user, "hao", "Haojue HJ125-8");
    expect(container.querySelector("table")).toBeNull();
    expect(container.innerHTML).not.toMatch(/overflow-x|w-max|min-w-max|w-screen/);
    expect(lineGroup(1).className).toMatch(/min-w-0/);
    await user.click(screen.getByRole("button", { name: "Retour aux achats" }));
    expect(router.state.location.search).toBe("");
  });
});
