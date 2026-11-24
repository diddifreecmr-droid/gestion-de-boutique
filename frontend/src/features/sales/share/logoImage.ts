/**
 * Logo du reçu pour le PDF (specs § 15.1) : lien signé court du DTO → image JPEG sur fond
 * blanc (un PNG transparent deviendrait noir), prête à embarquer (`pdfImage.ts`).
 *
 * Le logo est **facultatif** sur le reçu : lien expiré (410), image illisible ou coupure le
 * temps de la lire → `null`, et le PDF part avec le nom seul (repli voulu par la décision
 * client, jamais une erreur pour l'utilisateur). Toute autre panne (canvas absent) est relancée.
 */
import type { PdfImage } from "./pdfImage";

export const LOGO_JPEG_QUALITY = 0.85;

async function readable(url: string): Promise<Blob | null> {
  const response = await fetch(url).catch(() => null); // coupure : PDF sans logo
  if (response === null || !response.ok) return null;
  return response.blob();
}

export async function browserLogo(url: string): Promise<PdfImage | null> {
  const blob = await readable(url);
  if (blob === null) return null;
  const bitmap = await createImageBitmap(blob).catch(() => null); // image illisible
  if (bitmap === null) return null;
  const canvas = document.createElement("canvas");
  canvas.width = bitmap.width;
  canvas.height = bitmap.height;
  const context = canvas.getContext("2d");
  if (context === null) throw new Error("Canvas 2D indisponible : logo du PDF impossible");
  context.fillStyle = "#fff"; // papier blanc (§ 10 : noir sur blanc)
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(bitmap, 0, 0);
  bitmap.close();
  const jpeg = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (out) => {
        if (out === null) reject(new Error("Ré-encodage JPEG du logo impossible"));
        else resolve(out);
      },
      "image/jpeg",
      LOGO_JPEG_QUALITY,
    );
  });
  const bytes = new Uint8Array(await jpeg.arrayBuffer());
  return { jpeg: bytes, widthPx: canvas.width, heightPx: canvas.height };
}
