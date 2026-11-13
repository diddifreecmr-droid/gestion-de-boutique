/**
 * Enregistrer un fichier reçu (modèle `.xlsx`) dans le dossier « Téléchargements » : lien
 * temporaire vers le contenu, cliqué puis libéré. Injecté dans l'écran (les tests le remplacent :
 * jsdom n'a pas `URL.createObjectURL`).
 */
import type { TemplateFile } from "../../core/gateways/importsContract";

export type SaveFile = (file: TemplateFile) => void;

export const saveInBrowser: SaveFile = ({ blob, fileName }) => {
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    anchor.rel = "noopener";
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    // Libéré après le départ du téléchargement (le navigateur a déjà lu le lien au clic).
    setTimeout(() => {
      URL.revokeObjectURL(url);
    }, 0);
  }
};
