import { screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import { axeViolations } from "../../testing/axe";
import { json } from "../../testing/fakeApi";
import {
  entry,
  JOURNAL_ROUTES,
  memberSession,
  preloadLot1Screens,
  route,
  SHOP_PATH,
} from "../../testing/lot1Screens";
import { OWNER_ID, SELLER_ID } from "../../testing/receivables";
import { renderApp } from "../../testing/renderApp";

beforeAll(preloadLot1Screens);

const PATH = `${SHOP_PATH}/journal`;
const LIST = route("GET", "/audit");
const page = (items: ReturnType<typeof entry>[], next: string | null = null) =>
  json(200, { items, next_cursor: next });

const CANCEL = entry({
  id: "aud-2",
  performer: { user_id: OWNER_ID, role: "owner", device_id: null },
  action: "cancel",
  action_label: "Annuler",
  summary: "Annulation de la vente",
  reason: "Client parti sans payer",
  changes: [{ field: "status", before: "valid", after: "cancelled" }],
  sensitive: true,
});

const rows = async () =>
  within(await screen.findByRole("list", { name: "Entrées du journal" })).getAllByRole("listitem");

describe("Journal (UC-JRN-01)", () => {
  it("phrase complète, pastille « Sensible », motif et changements ; lecture seule ; axe", async () => {
    const { container, user } = renderApp(PATH, {
      ...memberSession("owner"),
      ...JOURNAL_ROUTES,
      [LIST]: page([entry(), CANCEL]),
    });
    const [created, cancelled] = await rows();
    if (created === undefined || cancelled === undefined) throw new Error("deux entrées");
    expect(created.textContent).toContain(
      "Ibrahim Sali (Vendeur) a créé la vente V-000124 : 1 moto Haojue HJ125-8, 780 000 FCFA",
    );
    expect(created.textContent).toContain("10/11/2026");
    expect(created.textContent).toContain("Ventes");
    expect(within(created).queryByText("Sensible")).toBeNull();
    expect(within(cancelled).getByText("Sensible")).toBeVisible();
    expect(cancelled).toHaveClass("border-danger");
    expect(cancelled.textContent).toContain("Awa Bello (Propriétaire) a annulé la vente V-000124");
    expect(cancelled.textContent).toContain("Motif : Client parti sans payer");
    await user.click(within(cancelled).getByRole("button", { name: "Voir les changements" }));
    expect(within(cancelled).getByText("status : valid → cancelled")).toBeVisible();
    // Lecture seule : aucune action de modification ou de suppression.
    for (const name of [/Modifier/, /Supprimer/, /Annuler/]) {
      expect(screen.queryByRole("button", { name })).toBeNull();
    }
    expect(await axeViolations(container)).toEqual([]);
  });

  it("filtres période, utilisateur, type et module → paramètres de l'API", async () => {
    const { user, fake } = renderApp(PATH, {
      ...memberSession("owner"),
      ...JOURNAL_ROUTES,
      [LIST]: page([entry()]),
      [route("GET", "/audit?from=2026-11-01")]: page([entry()]),
      [route("GET", "/audit?from=2026-11-01&to=2026-11-10")]: page([entry()]),
      [route("GET", `/audit?from=2026-11-01&to=2026-11-10&user_id=${SELLER_ID}`)]: page([entry()]),
      [route("GET", `/audit?from=2026-11-01&to=2026-11-10&user_id=${SELLER_ID}&action=cancel`)]:
        page([entry()]),
      [route(
        "GET",
        `/audit?from=2026-11-01&to=2026-11-10&user_id=${SELLER_ID}&action=cancel&module=sales`,
      )]: page([]),
    });
    await rows();
    await user.type(screen.getByLabelText("Du"), "2026-11-01");
    await user.type(screen.getByLabelText("Au"), "2026-11-10");
    await user.click(screen.getByRole("button", { name: "Filtres" }));
    await user.click(screen.getByRole("radio", { name: "Ibrahim Sali" }));
    await user.click(screen.getByRole("radio", { name: "Annuler" }));
    await user.click(screen.getByRole("radio", { name: "Ventes" }));
    expect(await screen.findByText("Aucune action ne correspond à ces filtres.")).toBeVisible();
    const last = fake.calls.at(-1);
    expect(last?.url).toContain("module=sales");
  });

  it("période incohérente : message, aucune requête", async () => {
    const { user, fake } = renderApp(PATH, {
      ...memberSession("owner"),
      ...JOURNAL_ROUTES,
      [LIST]: page([entry()]),
      [route("GET", "/audit?from=2026-11-10")]: page([entry()]),
    });
    await rows();
    await user.type(screen.getByLabelText("Du"), "2026-11-10");
    await user.type(screen.getByLabelText("Au"), "2026-11-01");
    expect(await screen.findByText("La date de fin doit suivre la date de début")).toBeVisible();
    expect(fake.calls.some((c) => c.url.includes("to=2026-11-01"))).toBe(false);
    expect(screen.queryByRole("list", { name: "Entrées du journal" })).toBeNull();
  });

  it("« Voir plus » ajoute la page suivante (curseur)", async () => {
    const { user } = renderApp(PATH, {
      ...memberSession("owner"),
      ...JOURNAL_ROUTES,
      [LIST]: page([entry()], "c2"),
      [route("GET", "/audit?cursor=c2")]: page([CANCEL]),
    });
    expect(await rows()).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "Voir plus" }));
    expect(await screen.findByText("Sensible")).toBeVisible();
    expect(await rows()).toHaveLength(2);
  });

  it("vendeur : le journal n'existe pas pour lui (page introuvable)", async () => {
    renderApp(PATH, memberSession("seller"));
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeVisible();
  });
});
