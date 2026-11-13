import { useId, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { CARD, PRESSABLE } from "./cardClasses";
import { requireText } from "./controlClasses";

export interface CollapsibleSectionProps {
  /** Titre de la section (« Stock », « Créances »), qui est aussi son nom accessible. */
  title: string;
  /** Résumé d'une ligne sous le titre, lisible section fermée (« 2 erreurs à traiter »). */
  summary?: ReactNode;
  /** Ouverte au premier affichage (ex. une alerte à traiter). */
  defaultOpen?: boolean;
  /** Niveau du titre : 2 par défaut (sous le titre d'écran). */
  level?: 2 | 3;
  children: ReactNode;
}

/**
 * Section repliable (§ 6.3, « le reste à un appui ») : en-tête carte de 56 px au moins, titre
 * à gauche, chevron à droite. Motif ARIA « accordéon » : le bouton est dans le titre, son
 * `aria-expanded` dit l'état. Le contenu fermé n'est pas monté (liste longue = DOM léger) ;
 * le panneau, lui, existe toujours : `aria-controls` désigne un élément.
 */
export function CollapsibleSection({
  title,
  summary,
  defaultOpen = false,
  level = 2,
  children,
}: CollapsibleSectionProps) {
  requireText("CollapsibleSection", "title", title);
  const [open, setOpen] = useState(defaultOpen);
  const titleId = useId();
  const panelId = useId();
  const Heading = level === 2 ? "h2" : "h3";
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-2">
      <Heading className="m-0">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => {
            setOpen((current) => !current);
          }}
          className={`flex min-h-(--control-lg) items-center gap-4 ${CARD} ${PRESSABLE}`}
        >
          <span className="flex min-w-0 flex-1 flex-col">
            <span id={titleId} className="text-title-sm font-semibold text-text">
              {title}
            </span>
            {summary !== undefined && (
              <span className="text-body font-normal text-text-muted">{summary}</span>
            )}
          </span>
          <ChevronDown
            aria-hidden="true"
            className={`size-6 shrink-0 text-primary transition-transform duration-(--duration-fast) ease-out ${open ? "rotate-180" : ""}`}
          />
        </button>
      </Heading>
      <div id={panelId} hidden={!open} className="flex flex-col gap-2">
        {open && children}
      </div>
    </section>
  );
}
