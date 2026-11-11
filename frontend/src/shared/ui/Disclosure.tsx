import { useId, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { buttonClasses } from "./buttonClasses";

export interface DisclosureProps {
  /** Libellé du bouton (« Plus de détails » par défaut, § 6.2). */
  label?: string;
  /** Ouvert au premier affichage (ex. un champ facultatif déjà rempli). */
  defaultOpen?: boolean;
  /** Champs facultatifs, affichés dans le même flux une fois ouvert (pas de fenêtre). */
  children: ReactNode;
}

/**
 * « Plus de détails » (P4, § 6.2) : bouton ghost pleine largeur avec chevron. Le contenu
 * fermé reste monté mais masqué (`hidden`) : aria-controls désigne toujours un élément.
 */
export function Disclosure({
  label = "Plus de détails",
  defaultOpen = false,
  children,
}: DisclosureProps) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  return (
    <div className="flex flex-col gap-4">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => {
          setOpen((current) => !current);
        }}
        className={buttonClasses("ghost", "md", true, false)}
      >
        <ChevronDown
          aria-hidden="true"
          className={`size-6 shrink-0 transition-transform duration-(--duration-fast) ease-out ${open ? "rotate-180" : ""}`}
        />
        <span>{label}</span>
      </button>
      <div id={panelId} hidden={!open} className="flex flex-col gap-4">
        {children}
      </div>
    </div>
  );
}
