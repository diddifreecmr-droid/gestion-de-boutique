import { useId, type ReactNode } from "react";
import { CollapsibleSection } from "../../shared/ui";
import { useFoldSections } from "./foldContext";

export interface SectionProps {
  title: string;
  /** Résumé lisible section fermée (tableau de bord seulement). */
  summary?: string;
  /** Ouverte d'emblée dans le tableau de bord (ex. une alerte à traiter). */
  defaultOpen?: boolean;
  children: ReactNode;
}

/**
 * Bloc titré de l'accueil (« Créances », « Stock »…) : titre de section relié à la région.
 * Dans le tableau de bord (`FoldSectionsContext`), le bloc est replié derrière son titre.
 */
export function Section({ title, summary, defaultOpen = false, children }: SectionProps) {
  const id = useId();
  const fold = useFoldSections();
  if (fold) {
    return (
      <CollapsibleSection
        title={title}
        defaultOpen={defaultOpen}
        {...(summary === undefined ? {} : { summary })}
      >
        {children}
      </CollapsibleSection>
    );
  }
  return (
    <section aria-labelledby={id} className="flex flex-col gap-2">
      <h2 id={id} className="m-0 text-title-sm font-semibold text-text">
        {title}
      </h2>
      {children}
    </section>
  );
}
