import { describe, expect, it, vi } from "vitest";
import { installmentReceipt, saleReceipt } from "../../../testing/receipts";
import { formatMoney } from "../../../shared/format";
import { charsPerLine, renderPdf, winAnsi } from "./pdfDocument";
import { installmentReceiptModel, saleReceiptModel, wrap } from "./receiptLayout";
import { pdfFile, shareReceipt, type ShareHost } from "./sharePdf";

const text = (bytes: Uint8Array) => new TextDecoder("latin1").decode(bytes);

describe("PDF texte minimal", () => {
  it("code les accents en WinAnsi, les espaces fines en espaces, l'inconnu en « ? »", () => {
    expect(winAnsi("é")).toEqual([0xe9]);
    expect(winAnsi("€—’")).toEqual([0x80, 0x97, 0x92]);
    expect(winAnsi("780 000")).toEqual([...winAnsi("780 000")]);
    expect(winAnsi("ő")).toEqual([0x6f]); // repli sans accent
    expect(winAnsi("中")).toEqual([0x3f]);
  });

  it("document valide : en-tête, polices Courier, table xref aux bons décalages", () => {
    const page = { widthMm: 58, heightMm: null, marginMm: 7, fontPt: 9 };
    const pdf = text(
      renderPdf([{ text: "Total (FCFA) \\ é" }, { text: "Gras", bold: true }], page),
    );
    expect(pdf.startsWith("%PDF-1.4\n")).toBe(true);
    expect(pdf.trimEnd().endsWith("%%EOF")).toBe(true);
    expect(pdf).toContain("/BaseFont /Courier /Encoding /WinAnsiEncoding");
    expect(pdf).toContain("(Total \\(FCFA\\) \\\\ \\351) Tj");
    expect(pdf).toContain("/F2 9 Tf");
    const xref = Number(/startxref\n(\d+)/.exec(pdf)?.[1]);
    expect(pdf.slice(xref, xref + 4)).toBe("xref");
    const offsets = [...pdf.slice(xref).matchAll(/^(\d{10}) 00000 n $/gm)].map((m) => Number(m[1]));
    offsets.forEach((offset, index) => {
      expect(pdf.slice(offset).startsWith(`${String(index + 1)} 0 obj`)).toBe(true);
    });
  });

  it("A4 : plusieurs pages quand le texte déborde", () => {
    const page = { widthMm: 210, heightMm: 297, marginMm: 12, fontPt: 10 };
    const lines = Array.from({ length: 150 }, (_, i) => ({ text: `ligne ${String(i)}` }));
    expect(text(renderPdf(lines, page))).toContain("/Count 3");
  });
});

describe("mise en page des reçus", () => {
  it("reçu de vente 58 mm : aucune ligne plus large que le papier, totaux et mentions", () => {
    const model = saleReceiptModel(saleReceipt());
    const width = charsPerLine(model.page);
    expect(width).toBeLessThan(30);
    expect(model.lines.every((line) => line.text.length <= width)).toBe(true);
    const all = model.lines.map((line) => line.text.trim()).join("\n");
    expect(all).toContain("Motos Garoua");
    const remaining = formatMoney(480_000);
    expect(model.lines.some((line) => line.text.endsWith(remaining))).toBe(true);
    expect(all).toContain("Reste à");
    expect(all).not.toContain("1 × 780\n"); // montant jamais coupé en deux
    expect(all).toContain("Châssis : LBX123");
    expect(all).toContain("Duplicata");
    expect(model.fileName).toBe("recu-V-000130.pdf");
    expect(model.lines.find((line) => line.text.includes("Total"))?.bold).toBe(true);
  });

  it("reçu de vente : libellé du rôle du vendeur donné par le reçu", () => {
    const model = saleReceiptModel(saleReceipt({ seller_role_label: "Employé" }));
    const all = model.lines.map((line) => line.text.trim()).join("
");
    expect(all).toContain("Employé : Issa Vendeur");
    expect(all).not.toContain("Vendeur : ");
  });

  it("A4 et reçu de versement « Soldé »", () => {
    const office = saleReceiptModel(
      saleReceipt({ printing: { ...saleReceipt().printing, receipt_format: "a4" } }),
    );
    expect([office.page.widthMm, office.page.heightMm]).toEqual([210, 297]);
    const paid = installmentReceiptModel(installmentReceipt());
    const all = paid.lines.map((line) => line.text).join("\n");
    expect(all).toContain("Reçu de versement");
    expect(all).toContain("MTN MoMo (MP-77)");
    expect(all).toContain("Soldé");
    expect(paid.fileName).toBe("recu-R-000002.pdf");
  });

  it("coupe aux espaces et tranche un mot trop long", () => {
    expect(wrap("un deux trois", 7)).toEqual(["un deux", "trois"]);
    expect(wrap("ABCDEFGHIJ", 4)).toEqual(["ABCD", "EFGH", "IJ"]);
    expect(wrap("   ", 4)).toEqual([]);
  });
});

describe("partage", () => {
  const source = { kind: "sale" as const, receipt: saleReceipt() };
  const host = (overrides: Partial<ShareHost> = {}): ShareHost => ({
    download: vi.fn(),
    ...overrides,
  });

  it("Web Share (fichiers) si l'appareil le permet", async () => {
    const share = vi.fn(() => Promise.resolve());
    const outcome = await shareReceipt(source, host({ canShare: () => true, share }));
    expect(outcome).toEqual({ kind: "shared" });
    const data = (share.mock.calls[0] as unknown as [ShareData])[0];
    expect(data.files?.[0]?.name).toBe("recu-V-000130.pdf");
    expect(data.files?.[0]?.type).toBe("application/pdf");
  });

  it("feuille fermée : annulé ; sans partage de fichiers : téléchargement explicite", async () => {
    const abort = () => Promise.reject(new DOMException("fermé", "AbortError"));
    expect(await shareReceipt(source, host({ canShare: () => true, share: abort }))).toEqual({
      kind: "cancelled",
    });
    const fallback = host({ canShare: () => false, share: vi.fn() });
    const outcome = await shareReceipt(source, fallback);
    expect(outcome).toEqual({ kind: "downloaded", fileName: "recu-V-000130.pdf" });
    expect(fallback.download).toHaveBeenCalledTimes(1);
    const failing = host({ canShare: () => true, share: () => Promise.reject(new Error("panne")) });
    await expect(shareReceipt(source, failing)).rejects.toThrow("panne");
  });

  it("le fichier produit est un PDF lisible", async () => {
    const file = pdfFile({ kind: "installment", receipt: installmentReceipt() });
    expect(text(new Uint8Array(await file.arrayBuffer())).startsWith("%PDF-1.4")).toBe(true);
  });
});
