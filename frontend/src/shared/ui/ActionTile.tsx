import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { FOCUS_OUTLINE, PRESS_TRANSITION, requireText } from "./controlClasses";

export interface ActionTileProps {
  icon: LucideIcon;
  /** Mot sous l'icône (P5 : une icône a toujours un mot). */
  label: string;
  onClick: () => void;
}

/** Grosse tuile d'accueil (§ 6.3) : icône --icon-lg + mot, 96 px de haut. */
export function ActionTile({ icon: Icon, label, onClick }: ActionTileProps) {
  requireText("ActionTile", "label", label);
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "flex min-h-24 w-full flex-col items-center justify-center gap-2 rounded-lg border " +
        "border-border bg-surface p-4 text-center text-label font-semibold text-primary " +
        `hover:bg-primary-soft active:bg-primary-soft ${PRESS_TRANSITION} ${FOCUS_OUTLINE}`
      }
    >
      <Icon aria-hidden="true" className="size-8 shrink-0" />
      <span>{label}</span>
    </button>
  );
}

/** Grille des tuiles : 2 par ligne (§ 6.3). */
export function ActionTileGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-2 gap-4">{children}</div>;
}
