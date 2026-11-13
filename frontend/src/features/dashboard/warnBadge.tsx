import type { ReactNode } from "react";
import { Badge } from "../../shared/ui";

/** Pastille d'avertissement d'une ligne quand il y a quelque chose à faire (`n > 0`). */
export function warn(n: number, word: string): { badge?: ReactNode } {
  return n > 0 ? { badge: <Badge status="warning">{word}</Badge> } : {};
}
