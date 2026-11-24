/**
 * Logo en tête du PDF partagé (specs § 15.1, design-system § 10) : image JPEG embarquée telle
 * quelle (`/DCTDecode`, aucune recompression), centrée, ≤ 60 % de la largeur utile, 40 mm et
 * 20 mm de haut au plus. Elle occupe la hauteur d'un nombre entier de lignes vides placées en
 * tête : pagination et hauteur du rouleau restent celles d'un texte (`pdfDocument.ts`).
 */
import { MM_TO_PT, type PdfPage } from "./pdfDocument";

export interface PdfImage {
  /** Octets JPEG (fond blanc : un rouleau thermique n'a pas de transparence). */
  jpeg: Uint8Array;
  widthPx: number;
  heightPx: number;
}

export interface PlacedImage {
  image: PdfImage;
  widthPt: number;
  heightPt: number;
  /** Lignes de texte laissées vides en tête pour l'image (marge comprise). */
  lines: number;
}

const MAX_WIDTH_MM = 40;
const MAX_HEIGHT_MM = 20;
const WIDTH_SHARE = 0.6;

export function placeImage(image: PdfImage, page: PdfPage, leading: number): PlacedImage {
  if (!(image.widthPx > 0 && image.heightPx > 0)) {
    throw new Error(
      `Logo du PDF sans dimensions (${String(image.widthPx)} × ${String(image.heightPx)})`,
    );
  }
  const usableMm = page.widthMm - 2 * page.marginMm;
  const widthMm = Math.min(usableMm * WIDTH_SHARE, MAX_WIDTH_MM);
  const ratio = image.heightPx / image.widthPx;
  const scale = Math.min(1, MAX_HEIGHT_MM / (widthMm * ratio));
  const widthPt = widthMm * scale * MM_TO_PT;
  const heightPt = widthMm * ratio * scale * MM_TO_PT;
  const step = page.fontPt * leading;
  return { image, widthPt, heightPt, lines: Math.ceil(heightPt / step) + 1 };
}

/** Opérateurs du contenu : l'image `/Im1` en haut de la zone utile, centrée. */
export function imageOps(placed: PlacedImage, page: PdfPage, widthPt: number, heightPt: number) {
  const x = (widthPt - placed.widthPt) / 2;
  const y = heightPt - page.marginMm * MM_TO_PT - placed.heightPt;
  const w = placed.widthPt.toFixed(2);
  const h = placed.heightPt.toFixed(2);
  return `q ${w} 0 0 ${h} ${x.toFixed(2)} ${y.toFixed(2)} cm /Im1 Do Q`;
}

/** Dictionnaire de l'objet image (le flux binaire suit, écrit par `renderPdf`). */
export function imageDictionary(image: PdfImage): string {
  return (
    `<< /Type /XObject /Subtype /Image /Width ${String(image.widthPx)} ` +
    `/Height ${String(image.heightPx)} /ColorSpace /DeviceRGB /BitsPerComponent 8 ` +
    `/Filter /DCTDecode /Length ${String(image.jpeg.length)} >>`
  );
}
