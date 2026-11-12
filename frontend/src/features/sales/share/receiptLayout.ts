/**
 * Mise en page texte d'un reçu pour le PDF partagé (UC-VEN-04, UC-CRE-03) : mêmes contenus que
 * `ReceiptDocument` / `InstallmentReceiptDocument` (rendus HTML de l'impression), même profil
 * de papier (58 mm, 80 mm, A5, A4 ; largeur, marge et taille du texte réglées par la boutique).
 */
import type { InstallmentReceipt } from "../../../core/gateways/receivablesContract";
import type { Receipt, ReceiptLine } from "../../../core/gateways/salesContract";
import { formatDate, formatMoney, formatQuantity, formatTime } from "../../../shared/format";
import { DEFAULT_PRINTING } from "../../receivables/receipt/printing";
import { printProfileOf } from "../receipt/printProfile";
import { charsPerLine, type PdfLine, type PdfPage } from "./pdfDocument";

export interface ReceiptPdfModel {
  page: PdfPage;
  lines: PdfLine[];
  fileName: string;
  title: string;
}

export function pageOf(printing: Receipt["printing"]): PdfPage {
  const profile = printProfileOf(printing.receipt_format);
  if (profile === "a4-a5") {
    const a5 = printing.receipt_format === "a5";
    return { widthMm: a5 ? 148 : 210, heightMm: a5 ? 210 : 297, marginMm: 12, fontPt: 10 };
  }
  const side = (printing.paper_width_mm - printing.printable_width_mm) / 2;
  return {
    widthMm: printing.paper_width_mm,
    heightMm: null,
    marginMm: side + printing.padding_mm,
    fontPt: printing.font_size_pt,
  };
}

/** Coupe aux espaces ; un mot plus long que la ligne est coupé net (rien n'est perdu). */
export function wrap(text: string, width: number): string[] {
  const out: string[] = [];
  let current = "";
  for (const word of text.split(/\s+/).filter((part) => part !== "")) {
    for (let rest = word; rest !== ""; rest = rest.slice(width)) {
      const piece = rest.slice(0, width);
      if (current === "") current = piece;
      else if (current.length + 1 + piece.length <= width) current = `${current} ${piece}`;
      else {
        out.push(current);
        current = piece;
      }
    }
  }
  return current === "" ? [] : [...out, current];
}

class Lines {
  readonly lines: PdfLine[] = [];
  constructor(readonly width: number) {}

  text(text: string, bold = false) {
    for (const line of wrap(text, this.width)) this.lines.push({ text: line, bold });
  }
  center(text: string, bold = false) {
    for (const line of wrap(text, this.width)) {
      const pad = Math.floor((this.width - line.length) / 2);
      this.lines.push({ text: " ".repeat(pad) + line, bold });
    }
  }
  /** Libellé à gauche, montant à droite ; à la ligne si la place manque. */
  row(label: string, value: string, bold = false) {
    const room = this.width - value.length - 1;
    const labels = room >= 4 ? wrap(label, room) : wrap(label, this.width);
    const last = labels.pop() ?? "";
    for (const line of labels) this.lines.push({ text: line, bold });
    if (last.length + 1 + value.length <= this.width) {
      const gap = this.width - last.length - value.length;
      this.lines.push({ text: last + " ".repeat(gap) + value, bold });
    } else {
      this.lines.push({ text: last, bold });
      this.lines.push({ text: value.padStart(this.width), bold });
    }
  }
  rule() {
    this.lines.push({ text: "-".repeat(this.width) });
  }
}

function details(detail: ReceiptLine["details"][number]): string {
  const parts: [string, string | null][] = [
    ["Couleur", detail.color],
    ["Châssis", detail.chassis_number],
    ["Moteur", detail.engine_number],
    ["Taille", detail.size],
  ];
  return parts
    .filter((part): part is [string, string] => part[1] !== null && part[1] !== "")
    .map(([label, value]) => `${label} : ${value}`)
    .join(" · ");
}

export function saleReceiptModel(receipt: Receipt): ReceiptPdfModel {
  const page = pageOf(receipt.printing);
  const out = new Lines(charsPerLine(page));
  const { header } = receipt;
  out.center(header.shop_name, true);
  out.center(header.city);
  if (header.address !== null) out.center(header.address);
  out.center(`Tél. ${header.phone}`);
  if (header.niu !== null) out.center(`NIU : ${header.niu}`);
  if (header.rccm !== null) out.center(`RCCM : ${header.rccm}`);
  out.rule();
  out.center(receipt.title, true);
  const provisional = receipt.provisional_number;
  out.text(`N° ${receipt.number}${provisional === null ? "" : ` (provisoire ${provisional})`}`);
  out.text(`Le ${formatDate(receipt.sold_at)} à ${formatTime(receipt.sold_at)}`);
  out.text(`Vendeur : ${receipt.seller_name}`);
  if (receipt.customer !== null) {
    out.text(`Client : ${receipt.customer.name} — ${receipt.customer.phone}`);
  }
  out.rule();
  for (const line of receipt.lines) {
    out.text(line.article_name);
    for (const detail of line.details) out.text(details(detail));
    const quantity = `${formatQuantity(line.quantity)} × ${formatMoney(line.unit_price)}`;
    out.row(quantity, formatMoney(line.line_total));
  }
  out.rule();
  out.row("Total", formatMoney(receipt.total), true);
  for (const payment of receipt.payments) {
    const reference = payment.reference === null ? "" : ` (${payment.reference})`;
    out.row(`Payé — ${payment.mode_name}${reference}`, formatMoney(payment.amount));
  }
  if (receipt.remaining > 0) out.row("Reste à payer", formatMoney(receipt.remaining), true);
  for (const mention of receipt.mentions) out.center(mention.label, true);
  if (receipt.footer_message !== null) {
    out.rule();
    out.center(receipt.footer_message);
  }
  return { page, lines: out.lines, fileName: `recu-${receipt.number}.pdf`, title: receipt.title };
}

export function installmentReceiptModel(receipt: InstallmentReceipt): ReceiptPdfModel {
  const page = pageOf(DEFAULT_PRINTING);
  const out = new Lines(charsPerLine(page));
  out.center(receipt.shop_name, true);
  if (receipt.shop_city !== null) out.center(receipt.shop_city);
  if (receipt.shop_phone !== null) out.center(`Tél. ${receipt.shop_phone}`);
  out.rule();
  out.center("Reçu de versement", true);
  out.text(`N° ${receipt.number}`);
  out.text(`Le ${formatDate(receipt.paid_on)}`);
  out.text(`Client : ${receipt.customer_name} — ${receipt.customer_phone}`);
  if (receipt.sale_number !== null) out.text(`Vente : ${receipt.sale_number}`);
  out.rule();
  out.row("Versement", formatMoney(receipt.amount), true);
  const reference = receipt.reference === null ? "" : ` (${receipt.reference})`;
  out.row("Mode", `${receipt.mode_name}${reference}`);
  out.row("Total déjà versé", formatMoney(receipt.total_paid));
  out.row("Reste à payer", formatMoney(receipt.remaining), true);
  if (receipt.nature === "recovery") out.center("Récupération sur perte", true);
  if (receipt.settled) out.center("Soldé", true);
  if (receipt.cancelled) out.center("Versement annulé", true);
  const title = "Reçu de versement";
  return { page, lines: out.lines, fileName: `recu-${receipt.number}.pdf`, title };
}
