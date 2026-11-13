import { useId, useRef, type KeyboardEvent } from "react";
import type { LucideIcon } from "lucide-react";
import { Check } from "lucide-react";
import { FOCUS_OUTLINE, PRESS_TRANSITION, requireText } from "./controlClasses";

export interface ChoiceOption<T extends string> {
  value: T;
  label: string;
  icon?: LucideIcon;
}

export interface ChoiceChipsProps<T extends string> {
  /** Libellé du groupe (« Paiement »), affiché au-dessus et relié au radiogroup. */
  label: string;
  options: readonly ChoiceOption<T>[];
  /** Choix actif ; l'écran présélectionne le dernier mode utilisé (§ 6.2). */
  value: T | null;
  onChange: (value: T) => void;
  /**
   * Pastilles compactes de 48 px, à la suite (taille, couleur d'une ligne de panier, § 7.4) ;
   * par défaut, grosses pastilles de 56 px, 2 par ligne.
   */
  compact?: boolean;
}

const NEXT_KEYS = new Set(["ArrowRight", "ArrowDown"]);
const PREVIOUS_KEYS = new Set(["ArrowLeft", "ArrowUp"]);

function chipClasses(active: boolean, compact: boolean): string {
  // Actif : bordure 1 px + ring intérieur 1 px = 2 px primary, sans décaler le contenu.
  const state = active
    ? "border-primary bg-primary-soft ring-1 ring-inset ring-primary"
    : "border-border-strong bg-surface hover:bg-primary-soft";
  const size = compact ? "min-h-(--control-md) min-w-(--control-md)" : "min-h-(--control-lg)";
  return (
    `flex ${size} items-center gap-2 rounded-md border px-4 text-left ` +
    `text-label font-semibold text-text ${PRESS_TRANSITION} ${FOCUS_OUTLINE} ${state}`
  );
}

/**
 * Choix exclusif en grosses pastilles de 56 px, 2 par ligne (§ 6.2). Motif ARIA
 * « radiogroup » : une seule tabulation pour le groupe, les flèches changent le choix.
 */
export function ChoiceChips<T extends string>({
  label,
  options,
  value,
  onChange,
  compact = false,
}: ChoiceChipsProps<T>) {
  const labelId = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  requireText("ChoiceChips", "label", label);
  if (options.length === 0) throw new Error("ChoiceChips : options ne peut pas être vide");
  const values = options.map((option) => option.value);
  if (new Set(values).size !== values.length) {
    throw new Error(`ChoiceChips : valeurs en double dans ${values.join(", ")}`);
  }
  if (value !== null && !values.includes(value)) {
    throw new Error(`ChoiceChips : la valeur « ${value} » n'est pas une option`);
  }
  const selectedIndex = value === null ? -1 : values.indexOf(value);
  const tabStop = selectedIndex === -1 ? 0 : selectedIndex;

  const select = (index: number) => {
    const count = options.length;
    const target = (index + count) % count;
    const option = options[target];
    if (option === undefined) throw new Error(`ChoiceChips : index ${String(target)} hors liste`);
    refs.current[target]?.focus();
    onChange(option.value);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (NEXT_KEYS.has(event.key)) select(index + 1);
    else if (PREVIOUS_KEYS.has(event.key)) select(index - 1);
    else return;
    event.preventDefault();
  };

  return (
    <div className="flex flex-col gap-2">
      <span id={labelId} className="text-label font-semibold text-text">
        {label}
      </span>
      <div
        role="radiogroup"
        aria-labelledby={labelId}
        className={compact ? "flex flex-wrap gap-2" : "grid grid-cols-2 gap-2"}
      >
        {options.map((option, index) => {
          const active = index === selectedIndex;
          const Icon = option.icon;
          return (
            <button
              key={option.value}
              ref={(element) => {
                refs.current[index] = element;
              }}
              type="button"
              role="radio"
              aria-checked={active}
              tabIndex={index === tabStop ? 0 : -1}
              onClick={() => {
                onChange(option.value);
              }}
              onKeyDown={(event) => {
                handleKeyDown(event, index);
              }}
              className={chipClasses(active, compact)}
            >
              {active && <Check aria-hidden="true" className="size-6 shrink-0 text-primary" />}
              {Icon !== undefined && <Icon aria-hidden="true" className="size-6 shrink-0" />}
              <span>{option.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
