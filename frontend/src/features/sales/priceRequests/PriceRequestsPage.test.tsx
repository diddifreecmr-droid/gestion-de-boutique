import { screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../../testing/axe";
import { SHOP_A } from "../../../testing/fakeApi";
import { seedPriceRequest } from "../../../testing/priceRequests";
import { money, plain, preloadSales, renderSale } from "../../../testing/renderSale";
import { modulesProfile, PROFILE } from "../../../testing/dashboard";
import { API } from "../../../testing/salesServer";
import { PRICE_REQUESTS_KEY } from "../salesNav";

beforeAll(async () => {
  await preloadSales();
  await Promise.all([import("./PriceRequestsRoute"), import("./PriceRequestsHomeCard")]);
});
beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-11T10:00:00Z"));
});
afterEach(() => {
  vi.useRealTimers();
});

const PAGE = `/s/${SHOP_A}/${PRICE_REQUESTS_KEY}`;

function openPage(path = PAGE) {
  const view = renderSale("owner", { path, extra: { [PROFILE]: modulesProfile() } });
  const request = seedPriceRequest(view.server);
  return { ...view, request };
}

async function row(name = "Haojue HJ125-8"): Promise<HTMLElement> {
  const list = await screen.findByRole("list", { name: "Demandes en attente" });
  const item = within(list).getByRole("heading", { name }).closest("li");
  if (item === null) throw new Error(`Demande « ${name} » absente`);
  return item;
}

describe("demandes de prix, côté propriétaire (UC-VEN-03, UC-TDB-01 point 6)", () => {
  it("tableau de bord : carte « Alertes en attente » avec le nombre, un appui ouvre la liste", async () => {
    const { user, container } = openPage(`/s/${SHOP_A}/tableau-de-bord`);
    const card = await screen.findByRole("list", { name: "Alertes en attente" });
    expect(await within(card).findByText("1 en attente de votre réponse")).toBeVisible();
    expect(within(card).getByText("À valider")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);
    await user.click(within(card).getByRole("button", { name: /Demandes de prix/ }));
    expect(await screen.findByRole("heading", { name: "Demandes de prix" })).toBeVisible();
  });

  it("liste : article, prix demandé, minimum, vendeur, temps restant ; 360 px", async () => {
    const { container } = openPage();
    const text = plain((await row()).textContent);
    expect(text).toContain(`Prix demandé${money(700_000)}`);
    expect(text).toContain(`Prix minimum${money(720_000)}`);
    expect(text).toContain("VendeurIssa Vendeur");
    expect(text).toContain("Expire dans30 min");
    expect(container.querySelector("table")).toBeNull();
    expect(container.innerHTML).not.toMatch(/overflow-x|w-max|min-w-max|w-screen/);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("accepter : confirmation légère, décision envoyée avec la version, la ligne s'en va", async () => {
    const { user, fake, server, request } = openPage();
    const item = within(await row());
    await user.click(item.getByRole("button", { name: "Accepter" }));
    expect(item.getByText(/Accepter 700\s000\sFCFA pour Haojue HJ125-8 \?/)).toBeVisible();
    await user.click(item.getByRole("button", { name: "Oui, accepter" }));
    expect(await screen.findByText("Aucune demande de prix en attente.")).toBeVisible();
    const post = fake.calls.find((c) => c.url === `${API}/price-requests/${request.id}/decision`);
    expect(post?.body).toEqual({ decision: "accept", version: 1 });
    expect(server.world.priceRequests.get(request.id)?.status).toBe("accepted");
    expect(await screen.findByText("Demande acceptée — Haojue HJ125-8")).toBeVisible();
  });

  it("refuser, ou revenir sans rien décider", async () => {
    const { user, server, request } = openPage();
    const item = within(await row());
    await user.click(item.getByRole("button", { name: "Refuser" }));
    await user.click(item.getByRole("button", { name: "Retour" }));
    expect(server.world.priceRequests.get(request.id)?.status).toBe("pending");
    await user.click(item.getByRole("button", { name: "Refuser" }));
    await user.click(item.getByRole("button", { name: "Oui, refuser" }));
    expect(await screen.findByText("Aucune demande de prix en attente.")).toBeVisible();
    expect(server.world.priceRequests.get(request.id)?.status).toBe("refused");
  });

  it("demande expirée avant la décision : message clair, la liste est relue", async () => {
    const { user } = openPage();
    const item = within(await row());
    vi.setSystemTime(new Date("2026-11-11T10:31:00Z"));
    await user.click(item.getByRole("button", { name: "Accepter" }));
    await user.click(item.getByRole("button", { name: "Oui, accepter" }));
    expect(
      await screen.findByText("Cette demande a expiré : le vendeur doit la refaire."),
    ).toBeVisible();
    expect(await screen.findByText("Aucune demande de prix en attente.")).toBeVisible();
  });

  it("vendeur : l'écran n'existe pas pour lui", async () => {
    renderSale("seller", { path: PAGE });
    expect(await screen.findByRole("heading", { name: /introuvable/i })).toBeVisible();
  });
});
