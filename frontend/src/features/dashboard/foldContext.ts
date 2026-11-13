import { createContext, useContext } from "react";

/**
 * Sections repliables du tableau de bord (audit UX du 13/11/2026) : sous ce contexte, chaque
 * `Section` (créances, stock, camions, jour par jour, alertes…) devient un en-tête d'un appui.
 * Hors du tableau de bord (accueils), les sections restent ouvertes et inchangées.
 */
export const FoldSectionsContext = createContext(false);

export function useFoldSections(): boolean {
  return useContext(FoldSectionsContext);
}
