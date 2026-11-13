import { useId, useRef, type KeyboardEvent } from "react";
import { Check } from "lucide-react";
import { FOCUS_OUTLINE, PRESS_TRANSITION, requireText } from "./controlClasses";

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
}

export interface SegmentedControlProps<T extends string> {
  /** Nom du groupe pour les lecteurs d'écran (« Vente au mètre ou à la pièce »). */
  label: string;
  /** Deux segments ou plus, pleine largeur ; un seul segment n'est pas un choix (fail-fast). */
  options: readonly SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
}

const NEXT_KEYS = new Set(["ArrowRight", "ArrowDown"]);
const PREVIOUS_KEYS = new Set(["ArrowLeft", "ArrowUp"]);

function segmentClasses(active: boolean): string {
  // Actif : bordure 2 px primary (1 px + ring intérieur 1 px), sans décaler le contenu.
  const state = active
    ? "z-10 border-primary bg-primary-soft ring-1 ring-inset ring-primary"
    : "border-border-strong bg-surface hover:bg-primary-soft";
  return (
    "flex min-h-(--control-lg) flex-1 items-center justify-center gap-2 border px-4 " +
    "text-label font-semibold text-text first:rounded-l-md last:rounded-r-md " +
    `-ml-px first:ml-0 ${PRESS_TRANSITION} ${FOCUS_OUTLINE} ${state}`
  );
}

/**
 * Bascule à segments accolés (design-system § 7.5) : 56 px, pleine largeur, segment actif en
 * `primary-soft` avec bordure 2 px `primary` et icône `Check` (la couleur ne porte jamais seule
 * l'information, P7). Motif ARIA « radiogroup » : une tabulation, les flèches changent le choix.
 */
export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
}: SegmentedControlProps<T>) {
  const labelId = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  requireText("SegmentedControl", "label", label);
  if (options.length < 2) throw new Error("SegmentedControl : deux segments au moins");
  const values = options.map((option) => option.value);
  const selected = values.indexOf(value);
  if (selected < 0) throw new Error(`SegmentedControl : « ${value} » n'est pas un segment`);

  const select = (index: number) => {
    const target = (index + options.length) % options.length;
    const option = options[target];
    if (option === undefined) throw new Error(`SegmentedControl : index ${String(target)}`);
    refs.current[target]?.focus();
    onChange(option.value);
  };
  const onKey = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (NEXT_KEYS.has(event.key)) select(index + 1);
    else if (PREVIOUS_KEYS.has(event.key)) select(index - 1);
    else return;
    event.preventDefault();
  };

  return (
    <div role="radiogroup" aria-labelledby={labelId} className="flex w-full">
      <span id={labelId} className="sr-only">
        {label}
      </span>
      {options.map((option, index) => {
        const active = index === selected;
        return (
          <button
            key={option.value}
            ref={(element) => {
              refs.current[index] = element;
            }}
            type="button"
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            onClick={() => {
              onChange(option.value);
            }}
            onKeyDown={(event) => {
              onKey(event, index);
            }}
            className={segmentClasses(active)}
          >
            {active && <Check aria-hidden="true" className="size-6 shrink-0 text-primary" />}
            <span>{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
