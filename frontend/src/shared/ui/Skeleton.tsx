export interface SkeletonProps {
  /** Nombre de blocs (lignes) affichés. */
  lines?: number;
  /** Texte lu par les lecteurs d'écran pendant le chargement. */
  label?: string;
}

/**
 * Chargement (§ 6.5) : blocs `border`, **sans animation** (pas de scintillement, P4).
 * Les blocs sont décoratifs ; seul le libellé « Chargement… » est annoncé.
 */
export function Skeleton({ lines = 3, label = "Chargement…" }: SkeletonProps) {
  if (!Number.isSafeInteger(lines) || lines < 1) {
    throw new Error(`Skeleton : lines doit être un entier ≥ 1, reçu ${String(lines)}`);
  }
  return (
    <div role="status" className="flex flex-col gap-2">
      <span className="sr-only">{label}</span>
      {Array.from({ length: lines }, (_, index) => (
        <span
          key={index}
          aria-hidden="true"
          className={`block h-6 rounded-md bg-border ${index === lines - 1 && lines > 1 ? "w-2/3" : "w-full"}`}
        />
      ))}
    </div>
  );
}
