/** Règles et textes de la navigation (design-system.md § 6.6), sans composant. */
import type { LucideIcon } from "lucide-react";
import { requireText } from "./controlClasses";

/** Au plus 5 entrées (CDC § 17.4, design-system § 6.6). */
export const MAX_NAV_ITEMS = 5;

export interface NavItem {
  key: string;
  label: string;
  icon: LucideIcon;
  href: string;
}

/** Vérifie les entrées et lève une erreur explicite (fail-fast). */
export function assertNavItems(items: readonly NavItem[], activeKey: string | null): void {
  if (items.length === 0) throw new Error("BottomNav : au moins une entrée est requise");
  if (items.length > MAX_NAV_ITEMS) {
    throw new Error(
      `BottomNav : ${String(items.length)} entrées, ${String(MAX_NAV_ITEMS)} au plus (CDC § 17.4)`,
    );
  }
  const keys = items.map((item) => item.key);
  if (new Set(keys).size !== keys.length) {
    throw new Error(`BottomNav : clés en double dans ${keys.join(", ")}`);
  }
  if (activeKey !== null && !keys.includes(activeKey)) {
    throw new Error(`BottomNav : l'entrée active « ${activeKey} » n'existe pas`);
  }
  items.forEach((item) => {
    requireText("BottomNav", "label", item.label);
  });
}

/** Plus de 99 alertes : « 99+ » (la pastille garde sa taille). */
export function alertBadgeText(count: number): string {
  return count > 99 ? "99+" : String(count);
}

/** Libellé accessible de la cloche, avec le nombre en toutes lettres de contexte. */
export function alertsLabel(count: number): string {
  if (count === 0) return "Alertes, aucune nouvelle";
  return count === 1 ? "Alertes, 1 nouvelle" : `Alertes, ${String(count)} nouvelles`;
}
