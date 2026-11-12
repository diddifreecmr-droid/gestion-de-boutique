/**
 * Préparation d'un fichier avant envoi (RG-T26, specs § 10 « Photos ») :
 *
 * - photo (tout format que le navigateur sait lire : JPG, PNG, WebP, HEIC selon l'appareil)
 *   → réduite à 1600 px au plus sur son grand côté, ré-encodée en JPEG qualité 0,7 ;
 * - PDF → envoyé tel quel s'il fait 5 Mo au plus ;
 * - tout autre fichier, ou au-delà de 5 Mo après réduction → `FileRejected` (message lisible).
 *
 * Le serveur revérifie format (premiers octets) et taille : ce contrôle n'est qu'un confort.
 */

export const MAX_BYTES = 5 * 1024 * 1024;
export const MAX_SIDE_PX = 1600;
export const JPEG_QUALITY = 0.7;

export class FileRejected extends Error {
  override name = "FileRejected";
}

export interface PreparedFile {
  blob: Blob;
  fileName: string;
}

/** Décodage et ré-encodage d'une image : remplacé dans les tests (jsdom n'a pas de canvas). */
export interface ImageCodec {
  reduce(file: Blob, maxSide: number, quality: number): Promise<Blob>;
}

export const canvasCodec: ImageCodec = {
  async reduce(file, maxSide, quality) {
    const bitmap = await createImageBitmap(file).catch((cause: unknown) => {
      throw new FileRejected("Image illisible : prenez une autre photo.", { cause });
    });
    const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    const context = canvas.getContext("2d");
    if (context === null) throw new Error("Canvas 2D indisponible : réduction impossible");
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    return new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (blob === null) reject(new Error("Ré-encodage JPEG impossible"));
          else resolve(blob);
        },
        "image/jpeg",
        quality,
      );
    });
  },
};

function baseName(name: string): string {
  const cleaned = name.replace(/\.[^.]*$/, "").replace(/[^\w-]+/g, "-");
  return cleaned === "" ? "photo" : cleaned.slice(0, 60);
}

export async function prepareFile(
  file: File,
  codec: ImageCodec = canvasCodec,
): Promise<PreparedFile> {
  if (file.type === "application/pdf") {
    if (file.size > MAX_BYTES) throw new FileRejected("PDF trop lourd : 5 Mo au plus.");
    return { blob: file, fileName: `${baseName(file.name)}.pdf` };
  }
  if (!file.type.startsWith("image/")) {
    throw new FileRejected("Format refusé : photo (JPG, PNG) ou document PDF.");
  }
  const reduced = await codec.reduce(file, MAX_SIDE_PX, JPEG_QUALITY);
  if (reduced.size > MAX_BYTES) throw new FileRejected("Photo trop lourde, même réduite.");
  return { blob: reduced, fileName: `${baseName(file.name)}.jpg` };
}
