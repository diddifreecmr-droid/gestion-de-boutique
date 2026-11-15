import { useState, type KeyboardEvent } from "react";
import { Plus, X } from "lucide-react";
import { Button, TextField } from "../../shared/ui";
import { addColors } from "./fabricDraft";

export interface ColorsInputProps {
  /** Couleurs déjà saisies (création) ; vide pour « Ajouter une couleur ». */
  value: readonly string[];
  onChange: (colors: string[]) => void;
  error?: string | undefined;
  /** Couleurs du tissu déjà en boutique : refusées ici (doublon). */
  existing?: readonly string[];
}

/**
 * Saisie rapide des couleurs d'un tissu (design-system § 7.6) : on tape « Rouge, Bleu, Vert »
 * puis « Ajouter » (ou Entrée) ; chaque couleur devient une pastille retirable.
 */
export function ColorsInput({ value, onChange, error, existing = [] }: ColorsInputProps) {
  const [typed, setTyped] = useState("");
  const taken = new Set(existing.map((color) => color.toLocaleLowerCase("fr")));
  const add = () => {
    const next = addColors(value, typed).filter(
      (color) => !taken.has(color.toLocaleLowerCase("fr")),
    );
    onChange(next);
    setTyped("");
  };
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    add();
  };
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-end gap-2">
        <div className="min-w-0 flex-1">
          <TextField
            label="Couleurs"
            hint="Séparez par une virgule : Rouge, Bleu, Vert"
            autoComplete="off"
            value={typed}
            error={error}
            onChange={(event) => {
              setTyped(event.target.value);
            }}
            onKeyDown={onKeyDown}
          />
        </div>
        <Button
          variant="secondary"
          icon={Plus}
          {...(typed.trim() === "" ? { disabledReason: "Tapez une couleur d'abord" } : {})}
          onClick={add}
        >
          Ajouter
        </Button>
      </div>
      {value.length > 0 && (
        <ul aria-label="Couleurs ajoutées" className="m-0 flex list-none flex-wrap gap-2 p-0">
          {value.map((color) => (
            <li key={color}>
              <Button
                variant="secondary"
                icon={X}
                aria-label={`Retirer ${color}`}
                onClick={() => {
                  onChange(value.filter((one) => one !== color));
                }}
              >
                {color}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
