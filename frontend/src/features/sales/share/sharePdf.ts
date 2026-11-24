/**
 * « Partager » un reçu en PDF (UC-VEN-04, H22, specs § 9 « Partage ») — module **chargé à la
 * demande** au premier appui (PERF-03) : rien de ceci n'alourdit le JavaScript initial.
 *
 * 1. Le PDF est produit sur l'appareil à partir du DTO du reçu (aucun service tiers), avec le
 *    logo de la boutique en tête si le reçu l'affiche (`show_logo`, `logo_url`).
 * 2. Web Share API niveau 2 (fichiers) si l'appareil sait partager ce PDF : feuille de partage
 *    du téléphone (WhatsApp…). L'utilisateur peut la fermer : résultat `cancelled`.
 * 3. Sinon, **repli explicite** : le PDF est téléchargé et l'écran le dit (`downloaded`).
 */
import type { InstallmentReceipt } from "../../../core/gateways/receivablesContract";
import type { Receipt } from "../../../core/gateways/salesContract";
import { browserLogo } from "./logoImage";
import { renderPdf } from "./pdfDocument";
import type { PdfImage } from "./pdfImage";
import { installmentReceiptModel, saleReceiptModel, type ReceiptPdfModel } from "./receiptLayout";

export type ShareableReceipt =
  { kind: "sale"; receipt: Receipt } | { kind: "installment"; receipt: InstallmentReceipt };

export type ShareOutcome =
  { kind: "shared" } | { kind: "cancelled" } | { kind: "downloaded"; fileName: string };

/** Ce que le module utilise du navigateur (remplacé dans les tests). */
export interface ShareHost {
  canShare?: (data: ShareData) => boolean;
  share?: (data: ShareData) => Promise<void>;
  download: (file: File) => void;
  /** Lecture du logo (lien signé) en JPEG ; `null` : PDF avec le nom seul. */
  loadLogo?: (url: string) => Promise<PdfImage | null>;
}

export function modelOf(source: ShareableReceipt): ReceiptPdfModel {
  return source.kind === "sale"
    ? saleReceiptModel(source.receipt)
    : installmentReceiptModel(source.receipt);
}

/** Adresse du logo à mettre en tête, ou `null` (reçu de versement, logo masqué ou absent). */
export function logoUrlOf(source: ShareableReceipt): string | null {
  if (source.kind !== "sale") return null;
  const { header } = source.receipt;
  return header.show_logo ? header.logo_url : null;
}

export function pdfFile(source: ShareableReceipt, logo: PdfImage | null = null): File {
  const model = modelOf(source);
  const bytes = renderPdf(model.lines, model.page, logo);
  return new File([bytes.slice().buffer], model.fileName, { type: "application/pdf" });
}

function downloadInBrowser(file: File): void {
  const url = URL.createObjectURL(file);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = file.name;
  anchor.rel = "noopener";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 60_000);
}

export function browserHost(): ShareHost {
  const nav = window.navigator;
  return {
    ...(typeof nav.canShare === "function" ? { canShare: (data) => nav.canShare(data) } : {}),
    ...(typeof nav.share === "function" ? { share: (data) => nav.share(data) } : {}),
    download: downloadInBrowser,
    loadLogo: browserLogo,
  };
}

export async function shareReceipt(
  source: ShareableReceipt,
  host: ShareHost = browserHost(),
): Promise<ShareOutcome> {
  const url = logoUrlOf(source);
  const logo = url === null || host.loadLogo === undefined ? null : await host.loadLogo(url);
  const file = pdfFile(source, logo);
  const data: ShareData = { files: [file], title: modelOf(source).title };
  if (host.share !== undefined && host.canShare?.(data) === true) {
    try {
      await host.share(data);
      return { kind: "shared" };
    } catch (error) {
      // Feuille de partage fermée par l'utilisateur : ce n'est pas une panne.
      if (error instanceof DOMException && error.name === "AbortError")
        return { kind: "cancelled" };
      throw error;
    }
  }
  host.download(file);
  return { kind: "downloaded", fileName: file.name };
}
