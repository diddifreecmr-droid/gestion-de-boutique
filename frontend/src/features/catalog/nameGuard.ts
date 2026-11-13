/**
 * Garde-fou du nom à la création (suivi du Lot 1, audit UX du 13/11/2026 : « Robe Bleu Marine
 * Robe »). Avant l'envoi, un nom qui répète un mot (« Robe Robe », ou une fin qui recopie le
 * début) est signalé avec le nom proposé ; un second appui crée l'article tel quel.
 */
import { articleTitle } from "../sales/articleTitle";
import type { FieldDraft } from "./fieldValues";

/** Nom que le serveur donnera à l'article : le champ « Nom », sinon marque + modèle (Motos). */
export function draftName(draft: FieldDraft): string {
  const name = (draft["name"] ?? "").trim();
  if (name !== "") return name;
  return [draft["brand"], draft["model"]]
    .map((part) => (part ?? "").trim())
    .filter((part) => part !== "")
    .join(" ");
}

/** Nom proposé si `name` répète un mot, sinon `null` (nom vide : rien à signaler). */
export function repeatedNameFix(name: string): string | null {
  const words = name.trim().split(/\s+/u).join(" ");
  if (words === "") return null;
  const fixed = articleTitle(words);
  return fixed === words ? null : fixed;
}
