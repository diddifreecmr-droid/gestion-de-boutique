import { act, screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { axeViolations } from "../../../testing/axe";
import { ownerDecides } from "../../../testing/priceRequests";
import {
  articleButton,
  preloadSales,
  priceField,
  renderSale,
  replaceText,
  saleAlert,
  sentSale,
  validateButton,
} from "../../../testing/renderSale";
import { API } from "../../../testing/salesServer";
import { EXPIRED_TEXT, ONE_ARTICLE_TEXT, PRICE_POLL_MS, REFUSED_TEXT } from "./priceRequestText";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-11T10:00:00Z"));
});
afterEach(() => {
  vi.useRealTimers();
});

const ASK = "Demander l'accord du propriétaire";
const REFRESH = "Actualiser l'état de la demande";

/** Vendeur : Haojue HJ125-8 à 700 000 (minimum 720 000), demande envoyée. */
async function askBelowMinimum() {
  const view = renderSale("seller", { priceApproval: true });
  await view.user.click(await articleButton("Haojue HJ125-8"));
  await replaceText(view.user, priceField(), "700000");
  await view.user.click(screen.getByRole("button", { name: ASK }));
  expect(await screen.findByText(/expire dans 30 min/)).toBeVisible();
  return view;
}

describe("accord du propriétaire, côté vendeur (UC-VEN-03)", () => {
  it("demande → accord → la vente part avec le price_request_id, l'accord ne ressert plus", async () => {
    const { user, server, recordSale, fake, container } = await askBelowMinimum();
    expect(fake.calls.filter((c) => c.url === `${API}/price-requests`)).toHaveLength(1);
    vi.setSystemTime(new Date("2026-11-11T10:05:00Z"));
    const accepted = ownerDecides(server, "accepted");
    await user.click(screen.getByRole("button", { name: REFRESH }));
    expect(await screen.findByText(/accord valable encore 30 min/)).toBeVisible();
    expect(screen.getByText("Accordé")).toBeVisible();
    expect(await axeViolations(container)).toEqual([]);

    await user.click(validateButton());
    expect(await screen.findByRole("heading", { name: /V-000124/ })).toBeVisible();
    expect(sentSale(recordSale).price_request_id).toBe(accepted.id);
    expect(server.world.priceRequests.get(accepted.id)?.sale_id).not.toBeNull();
  });

  it("refus : message clair, « Valider » bloqué jusqu'à un prix au minimum", async () => {
    const { user, server } = await askBelowMinimum();
    ownerDecides(server, "refused");
    await user.click(screen.getByRole("button", { name: REFRESH }));
    expect(await screen.findByText(REFUSED_TEXT)).toBeVisible();
    expect(validateButton()).toHaveAttribute("aria-disabled", "true");
    await replaceText(user, priceField(), "720000");
    expect(validateButton()).not.toHaveAttribute("aria-disabled");
  });

  it("expiration après 30 minutes : « Expirée », puis une nouvelle demande", async () => {
    const { user, fake } = await askBelowMinimum();
    vi.setSystemTime(new Date("2026-11-11T10:31:00Z"));
    await user.click(screen.getByRole("button", { name: REFRESH }));
    expect(await screen.findByText(EXPIRED_TEXT)).toBeVisible();
    await user.click(screen.getByRole("button", { name: ASK }));
    expect(await screen.findByText(/expire dans 30 min/)).toBeVisible();
    const posts = fake.calls.filter(
      (c) => c.method === "POST" && c.url === `${API}/price-requests`,
    );
    expect(posts).toHaveLength(2);
  });

  it("sondage toutes les 10 s tant que la demande attend (pas de notification, D19)", async () => {
    vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval"] });
    vi.setSystemTime(new Date("2026-11-11T10:00:00Z"));
    const { server, fake } = await askBelowMinimum();
    const reads = () => fake.calls.filter((c) => c.url.startsWith(`${API}/price-requests/`)).length;
    await act(() => vi.advanceTimersByTimeAsync(PRICE_POLL_MS));
    expect(reads()).toBe(1);
    ownerDecides(server, "accepted");
    await act(() => vi.advanceTimersByTimeAsync(PRICE_POLL_MS));
    expect(await screen.findByText("Accordé")).toBeVisible();
    await act(() => vi.advanceTimersByTimeAsync(PRICE_POLL_MS * 3));
    expect(reads()).toBe(2);
  });

  it("accord déjà utilisé : message du serveur, la demande est à refaire", async () => {
    const { user, server } = await askBelowMinimum();
    const accepted = ownerDecides(server, "accepted");
    await user.click(screen.getByRole("button", { name: REFRESH }));
    await screen.findByText("Accordé");
    server.world.priceRequests.set(accepted.id, { ...accepted, sale_id: "autre-vente" });
    await user.click(validateButton());
    expect(await saleAlert()).toHaveTextContent(
      "Cet accord a déjà servi pour une autre vente : demandez un nouvel accord.",
    );
    expect(screen.getByRole("button", { name: ASK })).toBeVisible();
  });

  it("refusée entre la relecture et l'envoi : le serveur le dit, l'écran suit", async () => {
    const { user, server } = await askBelowMinimum();
    const accepted = ownerDecides(server, "accepted");
    await user.click(screen.getByRole("button", { name: REFRESH }));
    await screen.findByText("Accordé");
    server.world.priceRequests.set(accepted.id, { ...accepted, status: "refused" });
    await user.click(validateButton());
    expect(await saleAlert()).toHaveTextContent(REFUSED_TEXT);
    expect(screen.getByText("Refusée")).toBeVisible();
  });

  it("deux articles sous le minimum : une demande n'en couvre qu'un", async () => {
    const { user } = renderSale("seller", { priceApproval: true });
    await user.click(await articleButton("Haojue HJ125-8"));
    await replaceText(user, priceField(), "700000");
    await user.click(screen.getByRole("button", { name: ASK }));
    await screen.findByText(/expire dans 30 min/);
    await user.click(screen.getByRole("button", { name: "Ajouter un article" }));
    await user.click(await articleButton("Sanya SY125-8"));
    const second = within(screen.getByRole("region", { name: "Sanya SY125-8" }));
    const field = second.getByLabelText("Prix");
    if (!(field instanceof HTMLInputElement)) throw new Error("« Prix » n'est pas un champ");
    await replaceText(user, field, "500000");
    expect(screen.queryByRole("button", { name: ASK })).toBeNull();
    expect(validateButton()).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText(ONE_ARTICLE_TEXT)).toBeInTheDocument();
  });

  it("hors connexion pendant la relecture : dit clairement, la demande reste suivie", async () => {
    const { user, network } = await askBelowMinimum();
    network.online = false;
    await user.click(screen.getByRole("button", { name: REFRESH }));
    expect(await saleAlert()).toHaveTextContent(/Connexion nécessaire : l'état de la demande/);
    expect(screen.getByText("En attente")).toBeVisible();
  });
});
