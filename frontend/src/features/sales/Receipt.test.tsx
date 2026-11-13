import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { Receipt } from "../../core/gateways/salesContract";
import { axeViolations } from "../../testing/axe";
import {
  articleButton,
  money,
  plain,
  preloadSales,
  renderSale,
  validateButton,
} from "../../testing/renderSale";
import { NOW, saleCommand } from "../../testing/salesFixtures";
import { addSale } from "../../testing/salesServer";
import { SHOP_A } from "../../testing/fakeApi";
import { pageRules, printProfileOf } from "./receipt/printProfile";
import { ReceiptDocument } from "./receipt/ReceiptDocument";

let print: ReturnType<typeof vi.spyOn>;
beforeAll(preloadSales);
beforeEach(() => {
  window.localStorage.clear();
  print = vi.spyOn(window, "print").mockImplementation(() => undefined);
});
afterEach(() => {
  vi.restoreAllMocks();
});

const receiptCalls = (calls: readonly { url: string }[]) =>
  calls.filter((c) => c.url.endsWith("/receipt")).length;

describe("reçu imprimable (UC-VEN-04, TR-18)", () => {
  it("« Imprimer » lit le reçu au moment d'imprimer, puis « Duplicata » à la réimpression", async () => {
    const { user, fake, container } = renderSale();
    await user.click(await articleButton("Haojue HJ125-8"));
    await user.click(validateButton());
    await screen.findByRole("heading", { name: /V-000124/ });
    expect(receiptCalls(fake.calls)).toBe(0);

    await user.click(screen.getByRole("button", { name: "Imprimer" }));
    const receipt = await screen.findByRole("article", { name: "Reçu" });
    expect(receiptCalls(fake.calls)).toBe(1);
    expect(print).toHaveBeenCalledTimes(1);
    expect(receipt).toHaveClass("receipt", "receipt--thermal-80");
    expect(plain(receipt.textContent)).toContain(`Total${money(780_000)}`);
    expect(plain(receipt.textContent)).toContain(`Payé — Espèces${money(780_000)}`);
    expect(within(receipt).queryByText("Duplicata")).toBeNull();
    expect(receipt.textContent).not.toMatch(/coût|marge|CMP/i);
    expect(container.querySelector("style")?.textContent).toContain("@page { size: 80mm auto;");
    expect(await axeViolations(container)).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Imprimer de nouveau" }));
    const again = await screen.findByText("Duplicata");
    expect(again).toHaveClass("receipt__mention");
    expect(receiptCalls(fake.calls)).toBe(2);
    expect(print).toHaveBeenCalledTimes(2);

    await user.click(screen.getByRole("button", { name: "Retour" }));
    expect(await screen.findByRole("heading", { name: /V-000124/ })).toBeVisible();
  });

  it("depuis la fiche : vente à crédit, « Vente à crédit » encadrée, aucun coût même propriétaire", async () => {
    const { user, server, router } = renderSale("owner", { path: `/s/${SHOP_A}/ventes` });
    const sale = await addSale(
      server,
      saleCommand({
        kind: "credit",
        customer: {
          id: "cus-moussa",
          name: "Moussa Abdou",
          phone: "+237690000000",
          kind: "individual",
        },
        payments: [{ mode_id: "pm-orange", amount: 300_000, reference: null }],
      }),
    );
    expect(sale.lines[0]?.frozen_last_cost).toBe(650_000);
    await router.navigate(`?id=${sale.id}`);
    await user.click(await screen.findByRole("button", { name: "Imprimer" }));
    const receipt = await screen.findByRole("article", { name: "Reçu" });
    expect(within(receipt).getByText("Vente à crédit")).toHaveClass("receipt__mention");
    expect(plain(receipt.textContent)).toContain(`Reste à payer${money(480_000)}`);
    expect(plain(receipt.textContent)).toContain("Couleur : Rouge · Châssis : LBX0001");
    expect(receipt.textContent).not.toMatch(/coût|marge|CMP|650 000/i);
    await user.click(screen.getByRole("button", { name: "Retour" }));
    expect(await screen.findByRole("heading", { name: `Vente ${sale.number}` })).toBeVisible();
  });
});

const RECEIPT: Receipt = {
  title: "Reçu de vente",
  header: {
    shop_name: "Motos Garoua",
    city: "Garoua",
    phone: "+237690000001",
    address: "Marché central",
    niu: "M0123456789",
    rccm: "RC/GRA/2024/B/12",
    show_logo: false,
  },
  sale_id: "s1",
  number: "V-000130",
  provisional_number: "P-07",
  sold_at: NOW,
  seller_name: "Issa Vendeur",
  customer: { name: "Moussa Abdou", phone: "+237690000000" },
  lines: [
    {
      article_name: "Haojue HJ125-8",
      sale_mode: "unit",
      quantity: "2",
      quantity_label: "2",
      unit_price: 750_000,
      line_total: 1_500_000,
      details: [
        { color: "Rouge", chassis_number: "LBX1", engine_number: null, size: null },
        { color: null, chassis_number: null, engine_number: "E2", size: "L" },
      ],
    },
  ],
  total: 1_500_000,
  paid: 1_500_000,
  payments: [{ mode_name: "Orange Money", amount: 1_500_000, reference: "OM-1" }],
  remaining: 0,
  mentions: [
    { code: "cancelled", label: "Annulé" },
    { code: "duplicate", label: "Duplicata" },
  ],
  footer_message: "Merci de votre confiance",
  printing: {
    receipt_format: "58mm",
    paper_width_mm: 58,
    printable_width_mm: 48,
    padding_mm: 2,
    font_size_pt: 9,
    copies: 1,
  },
  print_sequence: 2,
  printed_at: NOW,
};

describe("structure du reçu et profils d'impression", () => {
  it("contenu complet du CDC (en-tête, identification, client, lignes, totaux, mentions, pied)", async () => {
    const { container } = render(<ReceiptDocument receipt={RECEIPT} />);
    const receipt = screen.getByRole("article", { name: "Reçu" });
    expect(receipt).toHaveClass("receipt--thermal-58");
    const text = plain(receipt.textContent);
    for (const part of [
      "Motos Garoua",
      "Marché central",
      "Tél. +237690000001",
      "NIU : M0123456789",
      "RCCM : RC/GRA/2024/B/12",
      "Reçu de vente",
      "N° V-000130 (provisoire P-07)",
      "Vendeur : Issa Vendeur",
      "Client : Moussa Abdou — +237690000000",
      "Couleur : Rouge · Châssis : LBX1",
      "Moteur : E2 · Taille : L",
      `2 × ${money(750_000)}${money(1_500_000)}`,
      `Payé — Orange Money (OM-1)${money(1_500_000)}`,
      "Merci de votre confiance",
    ]) {
      expect(text).toContain(part);
    }
    expect(text).not.toContain("Reste à payer");
    expect(screen.getByText("Annulé")).toHaveClass("receipt__mention");
    expect(screen.getByText("Duplicata")).toHaveClass("receipt__mention");
    expect(container.querySelectorAll("hr.receipt__rule").length).toBeGreaterThanOrEqual(3);
    const rules = container.querySelector("style")?.textContent ?? "";
    expect(rules).toContain("@page { size: 58mm auto; margin: 0; }");
    expect(rules).toContain("font-size: 9pt; width: 48mm; padding: 2mm;");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("profils : 58 mm, 80 mm, A5 / A4 ; format inconnu refusé", () => {
    expect(printProfileOf("58mm")).toBe("thermal-58");
    expect(printProfileOf("80mm")).toBe("thermal-80");
    expect(printProfileOf("a5")).toBe("a4-a5");
    expect(printProfileOf("a4")).toBe("a4-a5");
    expect(() => printProfileOf("letter")).toThrow("Format de reçu inconnu");
    const office = { ...RECEIPT.printing, receipt_format: "a4", font_size_pt: 11 };
    expect(pageRules(office)).toBe(
      ["@page { size: A4; margin: 12mm; }", ".receipt { font-size: 11pt; }"].join("\n"),
    );
    expect(pageRules({ ...office, receipt_format: "a5" })).toContain("size: A5;");
  });
});
