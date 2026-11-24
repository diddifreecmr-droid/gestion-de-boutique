/**
 * Écriture d'un PDF texte minimal (PDF 1.4), sans dépendance : police standard **Courier**
 * (chasse fixe, toujours disponible dans un lecteur PDF, aucune police embarquée), codage
 * WinAnsi (accents français). Une ligne du modèle = une ligne du PDF ; la mise en page
 * (largeur en caractères, alignements) est faite par l'appelant (`receiptLayout.ts`).
 *
 * Module chargé à la demande (premier « Partager », PERF-03) : rien de ceci n'est dans le
 * JavaScript initial.
 */
import { imageDictionary, imageOps, placeImage, type PdfImage } from "./pdfImage";

export const MM_TO_PT = 72 / 25.4;
/** Avance d'un caractère Courier : 600/1000 de la taille du texte. */
export const COURIER_ADVANCE = 0.6;
const LEADING = 1.25;

export interface PdfLine {
  text: string;
  bold?: boolean;
}

export interface PdfPage {
  widthMm: number;
  /** Hauteur fixe (A4, A5) ; `null` = rouleau thermique, hauteur ajustée au contenu. */
  heightMm: number | null;
  marginMm: number;
  fontPt: number;
}

/** Caractères WinAnsi (cp1252) hors Latin-1 ; les autres : Latin-1 direct ou repli ASCII. */
// prettier-ignore
const CP1252: Readonly<Record<string, number>> = {
  "€": 0x80, "‚": 0x82, "ƒ": 0x83, "„": 0x84, "…": 0x85, "†": 0x86, "‡": 0x87, "ˆ": 0x88,
  "‰": 0x89, "Š": 0x8a, "‹": 0x8b, "Œ": 0x8c, "Ž": 0x8e, "‘": 0x91, "’": 0x92, "“": 0x93,
  "”": 0x94, "•": 0x95, "–": 0x96, "—": 0x97, "˜": 0x98, "™": 0x99, "š": 0x9a, "›": 0x9b,
  "œ": 0x9c, "ž": 0x9e, "Ÿ": 0x9f,
};
const SPACES = /[\u2000-\u200b\u202f\u205f]/g; // fines insécables de Intl (« 780 000 FCFA »)

/** Octets WinAnsi d'un texte ; un caractère sans équivalent devient « ? » (jamais omis). */
export function winAnsi(text: string): number[] {
  const bytes: number[] = [];
  for (const char of text.replace(SPACES, " ")) {
    const code = char.codePointAt(0) ?? 0x3f;
    if (code < 0x80 || (code >= 0xa0 && code <= 0xff)) bytes.push(code);
    else if (CP1252[char] !== undefined) bytes.push(CP1252[char]);
    else {
      const ascii = char.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      bytes.push(ascii.length === 1 && ascii.charCodeAt(0) < 0x80 ? ascii.charCodeAt(0) : 0x3f);
    }
  }
  return bytes;
}

/** Chaîne littérale PDF `( … )`, en ASCII : parenthèses et `\` échappés, octets ≥ 128 en octal. */
function literal(text: string): string {
  const parts = winAnsi(text).map((byte) => {
    if (byte === 0x28 || byte === 0x29 || byte === 0x5c) return `\\${String.fromCharCode(byte)}`;
    if (byte < 0x20 || byte >= 0x7f) return `\\${byte.toString(8).padStart(3, "0")}`;
    return String.fromCharCode(byte);
  });
  return `(${parts.join("")})`;
}

/** Nombre de caractères par ligne pour cette page (largeur utile ÷ avance Courier). */
export function charsPerLine(page: PdfPage): number {
  const usable = (page.widthMm - 2 * page.marginMm) * MM_TO_PT;
  return Math.max(10, Math.floor(usable / (COURIER_ADVANCE * page.fontPt)));
}

function pagesOf(lines: readonly PdfLine[], page: PdfPage): PdfLine[][] {
  if (page.heightMm === null) return [lines.slice()];
  const usable = (page.heightMm - 2 * page.marginMm) * MM_TO_PT;
  const perPage = Math.max(1, Math.floor(usable / (page.fontPt * LEADING)));
  const pages: PdfLine[][] = [];
  for (let start = 0; start < lines.length; start += perPage) {
    pages.push(lines.slice(start, start + perPage));
  }
  return pages.length === 0 ? [[]] : pages;
}

function contentStream(lines: readonly PdfLine[], page: PdfPage, heightPt: number): string {
  const step = page.fontPt * LEADING;
  const x = page.marginMm * MM_TO_PT;
  let y = heightPt - page.marginMm * MM_TO_PT - page.fontPt;
  const ops = lines.map((line) => {
    const op =
      `BT /${line.bold === true ? "F2" : "F1"} ${String(page.fontPt)} Tf ` +
      `1 0 0 1 ${x.toFixed(2)} ${y.toFixed(2)} Tm ${literal(line.text)} Tj ET`;
    y -= step;
    return op;
  });
  return ops.join("\n");
}

/** Octets d'un objet PDF : dictionnaire (et flux éventuel, ASCII ou binaire). */
function objectBytes(id: number, body: string, stream?: Uint8Array): Uint8Array[] {
  const ascii = new TextEncoder();
  if (stream === undefined) return [ascii.encode(`${String(id)} 0 obj\n${body}\nendobj\n`)];
  return [
    ascii.encode(`${String(id)} 0 obj\n${body}\nstream\n`),
    stream,
    ascii.encode("\nendstream\nendobj\n"),
  ];
}

function concat(chunks: readonly Uint8Array[]): Uint8Array {
  const out = new Uint8Array(chunks.reduce((total, chunk) => total + chunk.length, 0));
  let at = 0;
  for (const chunk of chunks) {
    out.set(chunk, at);
    at += chunk.length;
  }
  return out;
}

interface PdfObject {
  body: string;
  stream?: Uint8Array;
}

/**
 * Document PDF complet : catalogue, pages, deux polices, logo facultatif (1re page, JPEG
 * embarqué), table xref. Texte en ASCII ; seul le flux de l'image est binaire.
 */
export function renderPdf(
  textLines: readonly PdfLine[],
  page: PdfPage,
  image: PdfImage | null = null,
): Uint8Array {
  const placed = image === null ? null : placeImage(image, page, LEADING);
  const blank: PdfLine[] = Array.from({ length: placed?.lines ?? 0 }, () => ({ text: "" }));
  const lines = [...blank, ...textLines];
  const widthPt = page.widthMm * MM_TO_PT;
  const rollHeight = 2 * page.marginMm * MM_TO_PT + (lines.length + 1) * page.fontPt * LEADING;
  const heightPt = page.heightMm === null ? rollHeight : page.heightMm * MM_TO_PT;
  const pages = pagesOf(lines, page);
  const objects: PdfObject[] = [];
  const pageIds = pages.map((_, index) => 5 + 2 * index);
  const imageId = 5 + 2 * pages.length;
  const kids = pageIds.map((id) => `${String(id)} 0 R`).join(" ");
  const font = (name: string) =>
    `<< /Type /Font /Subtype /Type1 /BaseFont /${name} /Encoding /WinAnsiEncoding >>`;
  objects[1] = { body: "<< /Type /Catalog /Pages 2 0 R >>" };
  objects[2] = { body: `<< /Type /Pages /Kids [${kids}] /Count ${String(pages.length)} >>` };
  objects[3] = { body: font("Courier") };
  objects[4] = { body: font("Courier-Bold") };
  pages.forEach((pageLines, index) => {
    const id = pageIds[index] ?? 0;
    const withImage = placed !== null && index === 0;
    const text = contentStream(pageLines, page, heightPt);
    const stream = withImage ? `${imageOps(placed, page, widthPt, heightPt)}\n${text}` : text;
    const xobject = withImage ? ` /XObject << /Im1 ${String(imageId)} 0 R >>` : "";
    const box = `[0 0 ${widthPt.toFixed(2)} ${heightPt.toFixed(2)}]`;
    objects[id] = {
      body:
        `<< /Type /Page /Parent 2 0 R /MediaBox ${box} ` +
        `/Resources << /Font << /F1 3 0 R /F2 4 0 R >>${xobject} >> /Contents ${String(id + 1)} 0 R >>`,
    };
    objects[id + 1] = {
      body: `<< /Length ${String(stream.length)} >>\nstream\n${stream}\nendstream`,
    };
  });
  if (placed !== null) {
    objects[imageId] = { body: imageDictionary(placed.image), stream: placed.image.jpeg };
  }
  const chunks: Uint8Array[] = [new TextEncoder().encode("%PDF-1.4\n")];
  const offsets: number[] = [];
  let size = chunks[0]?.length ?? 0;
  for (let id = 1; id < objects.length; id += 1) {
    const object = objects[id];
    if (object === undefined) throw new Error(`Objet PDF ${String(id)} manquant`);
    offsets[id] = size;
    for (const chunk of objectBytes(id, object.body, object.stream)) {
      chunks.push(chunk);
      size += chunk.length;
    }
  }
  const entries = offsets.slice(1).map((at) => `${String(at).padStart(10, "0")} 00000 n \n`);
  const tail =
    `xref\n0 ${String(objects.length)}\n0000000000 65535 f \n${entries.join("")}` +
    `trailer\n<< /Size ${String(objects.length)} /Root 1 0 R >>\nstartxref\n${String(size)}\n%%EOF\n`;
  chunks.push(new TextEncoder().encode(tail));
  return concat(chunks);
}
