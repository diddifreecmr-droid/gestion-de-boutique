import type { ReactNode } from "react";

export interface ActionBarProps {
  /** Ligne au-dessus de l'action (ex. « Total 780 000 FCFA »). */
  summary?: ReactNode;
  /** L'action principale : un Button `lg` pleine largeur (P1, une seule par écran). */
  children: ReactNode;
  /** Fixée en bas de l'écran (défaut) ; `false` pour l'afficher dans le flux (vitrine). */
  fixed?: boolean;
}

/**
 * Barre d'action fixée en bas (§ 6.1) : `surface` + `--shadow-sheet`, padding --space-4,
 * plus la marge de sécurité basse de l'écran. L'écran garde un dégagement --space-7 (pb-12).
 */
export function ActionBar({ summary, children, fixed = true }: ActionBarProps) {
  const position = fixed ? "fixed inset-x-0 bottom-0 z-30" : "";
  return (
    <div className={`safe-bottom-4 bg-surface px-4 pt-4 shadow-sheet ${position}`}>
      <div className="mx-auto flex w-full max-w-150 flex-col gap-2">
        {summary !== undefined && <div className="text-lead text-text">{summary}</div>}
        {children}
      </div>
    </div>
  );
}
