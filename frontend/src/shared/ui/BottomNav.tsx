import type { MouseEvent } from "react";
import { FOCUS_OUTLINE, PRESS_TRANSITION } from "./controlClasses";
import { assertNavItems, type NavItem } from "./navigation";

export interface BottomNavProps {
  /** Entrées déjà filtrées par les droits (une entrée interdite n'est pas passée). */
  items: readonly NavItem[];
  activeKey: string | null;
  /** Interception par le routeur (navigation sans rechargement). */
  onNavigate?: (item: NavItem, event: MouseEvent<HTMLAnchorElement>) => void;
  /** Nom du repère de navigation. */
  label?: string;
  /** Fixée en bas de l'écran (défaut) ; `false` pour l'afficher dans le flux (vitrine). */
  fixed?: boolean;
}

/**
 * Barre du bas (§ 6.6) : icône + mot, 64 px, entrée active en primary avec un trait de
 * 3 px au-dessus et `aria-current="page"`. Marge de sécurité basse de l'écran incluse.
 */
export function BottomNav({
  items,
  activeKey,
  onNavigate,
  label = "Navigation principale",
  fixed = true,
}: BottomNavProps) {
  assertNavItems(items, activeKey);
  const position = fixed ? "fixed inset-x-0 bottom-0 z-30" : "";
  return (
    <nav
      aria-label={label}
      className={`safe-bottom-0 border-t border-border bg-surface ${position}`}
    >
      <ul className="m-0 flex list-none p-0">
        {items.map((item) => {
          const active = item.key === activeKey;
          const Icon = item.icon;
          const state = active
            ? "border-primary text-primary"
            : "border-transparent text-text-muted hover:text-primary";
          return (
            <li key={item.key} className="flex min-w-0 flex-1">
              <a
                href={item.href}
                aria-current={active ? "page" : undefined}
                onClick={(event) => {
                  onNavigate?.(item, event);
                }}
                className={
                  "flex h-16 w-full flex-col items-center justify-center gap-1 border-t-3 px-1 " +
                  `text-body font-semibold no-underline ${PRESS_TRANSITION} ${FOCUS_OUTLINE} ${state}`
                }
              >
                <Icon aria-hidden="true" className="size-6 shrink-0" />
                <span className="max-w-full truncate">{item.label}</span>
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
