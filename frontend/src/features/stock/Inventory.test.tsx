import { configure, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { isUuidV7 } from "../../core/api/uuidv7";
import { axeViolations } from "../../testing/axe";
import { apiError, json } from "../../testing/fakeApi";
import { money } from "../../testing/renderSale";
import { renderApp } from "../../testing/renderApp";
import {
  API,
  GAROUA,
  HAOJUE_ID,
  inventory,
  INVENTORY_ID,
  inventoryLine,
  STOCK_PAGE,
  stockRoutes,
  validatedInventory,
  YAMAHA_ID,
} from "../../testing/stock";

configure({ asyncUtilTimeout: 5000 });

beforeEach(() => {
  window.localStorage.clear();
});

const START = `${STOCK_PAGE}?vue=inventaire`;
const SHEET = `${START}&id=${INVENTORY_ID}`;
const BASE = `${API}/inventories/${INVENTORY_ID}`;
const GET = `GET ${BASE}`;
const bodyOf = (fake: { calls: { method: string; url: string; body: unknown }[] }, key: string) =>
  fake.calls.find((call) => `${call.method} ${call.url}` === key)?.body;

describe("inventaire — lancement et reprise (UC-STK-07)", () => {
  it("lance sur un lieu (id UUIDv7) ; le comptage ne montre jamais la quantité théorique", async () => {
    // Même si le serveur envoyait par erreur une quantité théorique, l'écran ne la lit pas.
    const leaky = inventory({
      lines: [inventoryLine({ theoretical: "7.000", difference: "-7.000" })],
    });
    const { user, fake, container, router } = renderApp(
      START,
      stockRoutes("accountant", {
        [`POST ${API}/inventories`]: json(201, inventory()),
        [GET]: json(200, leaky),
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Lancer l'inventaire" }));
    const field = await screen.findByLabelText("Haojue HJ125-8");
    expect(field).toHaveValue("");
    const body = bodyOf(fake, `POST ${API}/inventories`) as Record<string, unknown>;
    expect(body["location_id"]).toBe(GAROUA);
    expect(isUuidV7(String(body["id"]))).toBe(true);
    expect(router.state.location.search).toBe(`?vue=inventaire&id=${INVENTORY_ID}`);
    expect(container).not.toHaveTextContent(/théorique|prévue|7/);
    expect(screen.getByText("0 sur 1 articles comptés")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("un inventaire est déjà en cours dans ce lieu : propose de le reprendre", async () => {
    const open = apiError(422, "INVENTORY_IN_PROGRESS", "Déjà en cours", {
      location_id: GAROUA,
      inventory_id: INVENTORY_ID,
    });
    const { user, router } = renderApp(
      START,
      stockRoutes("owner", { [`POST ${API}/inventories`]: open, [GET]: json(200, inventory()) }),
    );
    await user.click(await screen.findByRole("button", { name: "Lancer l'inventaire" }));
    await user.click(
      await screen.findByRole("button", { name: "Reprendre l'inventaire en cours" }),
    );
    expect(router.state.location.search).toBe(`?vue=inventaire&id=${INVENTORY_ID}`);
    expect(await screen.findByLabelText("Yamaha Crypton")).toBeVisible();
  });
});

describe("inventaire — comptage, validation, abandon", () => {
  it("enregistre, valide, demande les motifs des écarts puis montre les écarts", async () => {
    const counted = inventory({
      version: 2,
      sales_since_start: 2,
      sales_message: "2 ventes enregistrées depuis le début du comptage",
      lines: [
        inventoryLine({ counted: "1.000" }),
        inventoryLine({ article_id: YAMAHA_ID, display_name: "Yamaha Crypton", counted: "0.000" }),
      ],
    });
    const validated = validatedInventory();
    const lacking = apiError(400, "VALIDATION_ERROR", "Motif obligatoire", {
      field: "reasons",
      articles: [HAOJUE_ID],
    });
    const { user, fake, container } = renderApp(
      SHEET,
      stockRoutes("owner", {
        [GET]: json(200, inventory({ sales_message: counted.sales_message })),
        [`PUT ${BASE}/counts`]: json(200, counted),
        [`POST ${BASE}/validate`]: [lacking, json(200, validated)],
      }),
    );
    expect(
      await screen.findByText("2 ventes enregistrées depuis le début du comptage"),
    ).toBeVisible();
    expect(screen.getByText("Il reste 2 article(s) à compter.")).toBeVisible();
    await user.type(screen.getByLabelText("Haojue HJ125-8"), "1");
    await user.type(screen.getByLabelText("Yamaha Crypton"), "0");
    await user.click(screen.getByRole("button", { name: "Valider l'inventaire" }));
    expect(bodyOf(fake, `PUT ${BASE}/counts`)).toEqual({
      version: 1,
      counts: [
        { article_id: HAOJUE_ID, counted: "1" },
        { article_id: YAMAHA_ID, counted: "0" },
      ],
    });
    expect(await screen.findByLabelText("Motif — Haojue HJ125-8")).toBeVisible();
    expect(container).not.toHaveTextContent(/théorique/);
    await user.click(screen.getByRole("button", { name: "Valider avec ces motifs" }));
    expect(
      screen.getByText("Donnez un motif pour chaque écart, ou un motif global."),
    ).toBeVisible();
    expect(fake.count(`POST ${BASE}/validate`)).toBe(1);
    await user.type(screen.getByLabelText("Motif global (pour tous les écarts)"), "Casse");
    await user.click(screen.getByRole("button", { name: "Valider avec ces motifs" }));
    const gaps = await screen.findByRole("list", { name: "Écarts d'inventaire" });
    expect(fake.calls.filter((c) => c.url.endsWith("/validate")).at(-1)?.body).toEqual({
      version: 2,
      reasons: [],
      global_reason: "Casse",
    });
    expect(fake.count(`PUT ${BASE}/counts`)).toBe(1);
    const gap = within(gaps).getByRole("listitem");
    expect(gap).toHaveTextContent("Quantité prévue (théorique)2");
    expect(gap).toHaveTextContent("Quantité comptée1");
    expect(gap).toHaveTextContent("Écart−1");
    expect(gap).toHaveTextContent("Valeur de l'écart (CMP)non calculable");
    expect(gap).toHaveTextContent("MotifCasse");
    expect(screen.getByText("Validé")).toBeVisible();
    expect(screen.getByText("1 article(s) sans écart.")).toBeVisible();
    expect(container).toHaveTextContent("Valeur des écarts (CMP)non calculable");
    expect(container).not.toHaveTextContent(money(0));
  });

  it("enregistre le comptage pour reprendre plus tard ; une saisie fausse est signalée", async () => {
    const { user, fake } = renderApp(
      SHEET,
      stockRoutes("owner", {
        [GET]: json(200, inventory()),
        [`PUT ${BASE}/counts`]: json(200, inventory({ version: 2 })),
      }),
    );
    await user.type(await screen.findByLabelText("Haojue HJ125-8"), "1,5");
    await user.click(screen.getByRole("button", { name: "Enregistrer le comptage" }));
    expect(await screen.findByText("Cet article se compte en nombre entier")).toBeVisible();
    expect(fake.count(`PUT ${BASE}/counts`)).toBe(0);
    await user.clear(screen.getByLabelText("Haojue HJ125-8"));
    await user.type(screen.getByLabelText("Haojue HJ125-8"), "3");
    await user.click(screen.getByRole("button", { name: "Enregistrer le comptage" }));
    expect(await screen.findByText(/Comptage enregistré/)).toBeVisible();
  });

  it("abandon avec confirmation ; conflit de version proposé au rechargement", async () => {
    const conflict = apiError(409, "VERSION_CONFLICT", "Version périmée");
    const { user, fake, router } = renderApp(
      SHEET,
      stockRoutes("owner", {
        [GET]: json(200, inventory()),
        [`POST ${BASE}/abandon`]: [conflict, json(200, inventory({ status: "abandoned" }))],
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Abandonner l'inventaire" }));
    const dialog = screen.getByRole("dialog", { name: "Abandonner l'inventaire INV-000001 ?" });
    await user.click(within(dialog).getByRole("button", { name: "Abandonner" }));
    expect(await screen.findByRole("button", { name: "Recharger l'inventaire" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Abandonner l'inventaire" }));
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Abandonner" }),
    );
    expect(await screen.findByText("Inventaire INV-000001 abandonné")).toBeVisible();
    expect(bodyOf(fake, `POST ${BASE}/abandon`)).toEqual({ version: 1 });
    expect(router.state.location.search).toBe("?vue=inventaire");
  });

  it("un inventaire abandonné : le stock n'a pas changé", async () => {
    renderApp(
      SHEET,
      stockRoutes("owner", { [GET]: json(200, inventory({ status: "abandoned" })) }),
    );
    expect(await screen.findByText(/a été abandonné/)).toBeVisible();
  });
});
