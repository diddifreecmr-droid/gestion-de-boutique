import { screen } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { SaleReturnCommand } from "../../../core/gateways/returnsContract";
import { axeViolations } from "../../../testing/axe";
import { articleButton, plain, preloadSales } from "../../../testing/renderSale";
import { NOW } from "../../../testing/salesFixtures";
import { ONE_SANYA, openSaleSheet } from "../../../testing/salesReturns";

beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(NOW)); // vente et jour : 11/11/2026
});
afterEach(() => {
  vi.useRealTimers();
});

const ALLOWED = { days: 7, employeeAllowed: true };
/** 20/11 : deux jours après la fin du délai (vente du 11, délai 7 → jusqu'au 18 inclus). */
const LATE = new Date("2026-11-20T10:00:00Z");

async function fillExchange(user: Awaited<ReturnType<typeof openSaleSheet>>["user"]) {
  await user.click(
    screen.getByRole("button", { name: "Quantité rendue — Sanya SY125-8 : plus un" }),
  );
  await user.type(screen.getByLabelText(/^Motif/), "Le client préfère la Haojue");
  await user.click(await articleButton("Haojue HJ125-8"));
}

describe("échange par l'employé (QC-4, EXC-L3-04/05)", () => {
  it("réglage désactivé (défaut) : aucun bouton « Échanger »", async () => {
    await openSaleSheet("seller", ONE_SANYA);
    expect(await screen.findByRole("button", { name: "Signaler une erreur" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Échanger" })).toBeNull();
    expect(screen.queryByText(/Échange possible/)).toBeNull();
  });

  it("réglage actif, sa vente, dans le délai : délai affiché, échange seul, sans coût ; axe", async () => {
    const { user, server, container } = await openSaleSheet("seller", ONE_SANYA, {}, ALLOWED);
    expect(await screen.findByText("Échange possible jusqu'au 18/11")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Échanger" }));
    expect(await screen.findByRole("heading", { name: /^Échange — V-/ })).toBeVisible();
    expect(screen.queryByRole("radiogroup", { name: "Type de retour" })).toBeNull();
    await fillExchange(user);
    expect(container.textContent).not.toMatch(/coût|marge|CMP/i);
    expect(await axeViolations(container)).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Enregistrer l'échange" }));
    expect(await screen.findByText(/^Échange enregistré — nouvelle vente/)).toBeVisible();
    const body = server.recordReturn.mock.calls[0]?.[1] as SaleReturnCommand;
    expect(body.refund).toBeNull();
    expect(body.exchange?.sale.payments).toEqual([
      { mode_id: "pm-cash", amount: 130_000, reference: null },
    ]);
  });

  it("hors délai : message clair, pas de bouton", async () => {
    vi.setSystemTime(LATE);
    await openSaleSheet("seller", ONE_SANYA, {}, ALLOWED);
    expect(
      await screen.findByText(
        "Délai d'échange dépassé (jusqu'au 18/11) : seul le propriétaire peut encore échanger cette vente.",
      ),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: "Échanger" })).toBeNull();
  });

  it("réglage retiré entre-temps : le refus 403 du serveur est expliqué", async () => {
    const { user, server } = await openSaleSheet("seller", ONE_SANYA, {}, ALLOWED);
    await user.click(await screen.findByRole("button", { name: "Échanger" }));
    await screen.findByRole("heading", { name: /^Échange — V-/ });
    await fillExchange(user);
    server.exchange = { ...ALLOWED, employeeAllowed: false };
    await user.click(screen.getByRole("button", { name: "Enregistrer l'échange" }));
    expect(await screen.findByText(/n'est pas autorisé dans cette boutique/)).toBeVisible();
  });
});

describe("échange hors délai par le propriétaire (QC-4, EXC-L3-03)", () => {
  it("délai affiché ; hors délai, confirmation « inscrit au journal » avant l'envoi", async () => {
    vi.setSystemTime(LATE);
    const { user, server } = await openSaleSheet("owner", ONE_SANYA, {}, ALLOWED);
    expect(
      await screen.findByText(
        "Délai d'échange dépassé (jusqu'au 18/11) : un échange sera inscrit au journal.",
      ),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Retour ou échange" }));
    await screen.findByRole("heading", { name: /Retour ou échange/ });
    await user.click(screen.getByRole("radio", { name: "Échange" }));
    await fillExchange(user);
    await user.click(screen.getByRole("button", { name: "Enregistrer l'échange" }));
    const dialog = await screen.findByRole("dialog", { name: "Échange hors délai ?" });
    expect(plain(dialog.textContent)).toContain("inscrit au journal");
    expect(server.recordReturn).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Échanger hors délai" }));
    expect(await screen.findByText(/^Échange enregistré — nouvelle vente/)).toBeVisible();
    const body = server.recordReturn.mock.calls[0]?.[1] as SaleReturnCommand;
    expect(body.exchange?.sale.payments).toEqual([
      { mode_id: "pm-cash", amount: 130_000, reference: null },
    ]);
  });
});
