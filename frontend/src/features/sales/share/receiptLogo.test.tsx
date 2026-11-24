import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { saleReceipt } from "../../../testing/receipts";
import { ReceiptDocument } from "../receipt/ReceiptDocument";
import { renderPdf } from "./pdfDocument";
import type { PdfImage } from "./pdfImage";
import { pdfFile, shareReceipt, type ShareHost } from "./sharePdf";

const text = (bytes: Uint8Array) => new TextDecoder("latin1").decode(bytes);
/** JPEG factice : octets binaires (≥ 0x80) gardés tels quels dans le flux de l'image. */
const LOGO: PdfImage = {
  jpeg: new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 0x80, 0x00, 0xfe, 0xff, 0xd9]),
  widthPx: 200,
  heightPx: 100,
};
const URL_LOGO = "https://api.test/api/v1/shops/s/attachments/a/content?expires=1&signature=x";
const withLogo = (show: boolean) =>
  saleReceipt({ header: { ...saleReceipt().header, show_logo: show, logo_url: URL_LOGO } });

async function pdfBytes(file: File): Promise<Uint8Array> {
  return new Uint8Array(await file.arrayBuffer());
}

describe("logo en tête du PDF partagé (specs § 15.1)", () => {
  it("JPEG embarqué intact (/DCTDecode), 1re page, xref aux bons décalages", () => {
    const page = { widthMm: 80, heightMm: null, marginMm: 6, fontPt: 11 };
    const bytes = renderPdf([{ text: "Motos Garoua", bold: true }], page, LOGO);
    const pdf = text(bytes);
    expect(pdf).toContain("/Subtype /Image /Width 200 /Height 100");
    expect(pdf).toContain("/Filter /DCTDecode /Length 9");
    expect(pdf).toContain("/XObject << /Im1 7 0 R >>");
    expect(pdf).toMatch(/q [\d.]+ 0 0 [\d.]+ [\d.]+ [\d.]+ cm \/Im1 Do Q/);
    const at = pdf.indexOf("stream\nÿØ");
    expect(Array.from(bytes.slice(at + 7, at + 16))).toEqual(Array.from(LOGO.jpeg));
    const xref = Number(/startxref\n(\d+)/.exec(pdf)?.[1]);
    expect(pdf.slice(xref, xref + 4)).toBe("xref");
    const offsets = [...pdf.slice(xref).matchAll(/^(\d{10}) 00000 n $/gm)].map((m) => Number(m[1]));
    offsets.forEach((offset, index) => {
      expect(pdf.slice(offset).startsWith(`${String(index + 1)} 0 obj`)).toBe(true);
    });
  });

  it("« afficher le logo » : le logo est lu puis mis en tête ; sinon ni lecture ni image", async () => {
    const download = vi.fn<ShareHost["download"]>();
    const loadLogo = vi.fn<NonNullable<ShareHost["loadLogo"]>>(() => Promise.resolve(LOGO));
    await shareReceipt({ kind: "sale", receipt: withLogo(true) }, { download, loadLogo });
    expect(loadLogo).toHaveBeenCalledWith(URL_LOGO);
    const shown = download.mock.calls[0]?.[0];
    expect(text(await pdfBytes(shown as File))).toContain("/DCTDecode");
    loadLogo.mockClear();
    await shareReceipt({ kind: "sale", receipt: withLogo(false) }, { download, loadLogo });
    expect(loadLogo).not.toHaveBeenCalled();
  });

  it("logo illisible ou lien expiré (`null`) : le PDF part avec le nom seul", async () => {
    const download = vi.fn<ShareHost["download"]>();
    const loadLogo = vi.fn(() => Promise.resolve(null));
    await shareReceipt({ kind: "sale", receipt: withLogo(true) }, { download, loadLogo });
    const pdf = text(await pdfBytes(download.mock.calls[0]?.[0] as File));
    expect(pdf).not.toContain("/XObject");
    expect(pdf).toMatch(/\( *Motos Garoua *\) Tj/);
    expect(text(await pdfBytes(pdfFile({ kind: "sale", receipt: withLogo(true) })))).not.toContain(
      "/Image",
    );
  });
});

describe("logo du reçu imprimé", () => {
  it("affiché en tête si « afficher le logo » ; masqué si l'image ne se charge pas", () => {
    render(<ReceiptDocument receipt={withLogo(true)} />);
    const logo = screen.getByRole("img", { name: "Logo de Motos Garoua" });
    expect(logo).toHaveAttribute("src", URL_LOGO);
    expect(logo).toHaveClass("receipt__logo");
    fireEvent.error(logo);
    expect(logo).not.toBeVisible();
  });

  it("logo masqué dans les réglages : le nom seul", () => {
    render(<ReceiptDocument receipt={withLogo(false)} />);
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByRole("heading", { name: "Motos Garoua" })).toBeVisible();
  });
});
