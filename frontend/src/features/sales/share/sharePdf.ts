/**
 * « Partager » un reçu en PDF (UC-VEN-04, H22, specs § 9 « Partage ») — module **chargé à la
 * demande** au premier appui (PERF-03) : rien de ceci n'alourdit le JavaScript initial.
 *
 * 1. Le PDF est produit sur l'appareil à partir du DTO du reçu (aucun service tiers).
 * 2. Web Share API niveau 2 (fichiers) si l'appareil sait partager ce PDF : feuille de partage
 *    du téléphone (WhatsApp…). L'utilisateur peut la fermer : résultat `cancelled`.
 * 3. Sinon, **repli explicite** : le PDF est téléchargé et l'écran le dit (`downloaded`).
 */
import type { InstallmentReceipt } from "../../../core/gateways/receivablesContract";
import type { Receipt } from "../../../core/gateways/salesContract";
import { renderPdf } from "./pdfDocument";
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
}

export function modelOf(source: ShareableReceipt): ReceiptPdfModel {
  return source.kind === "sale"
    ? saleReceiptModel(source.receipt)
    : installmentReceiptModel(source.receipt);
}

export function pdfFile(source: ShareableReceipt): File {
  const model = modelOf(source);
  const bytes = renderPdf(model.lines, model.page);
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
  };
}

export async function shareReceipt(
  source: ShareableReceipt,
  host: ShareHost = browserHost(),
): Promise<ShareOutcome> {
  const file = pdfFile(source);
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
