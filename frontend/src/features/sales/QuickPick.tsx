import { useState } from "react";
import { ChoiceChips, TextField } from "../../shared/ui";

/** Valeur de la pastille « Autre » (jamais envoyée : c'est le texte saisi qui part). */
const OTHER = "__autre__";

export interface QuickPickProps {
  /** « Taille », « Couleur » : libellé du groupe et du champ libre (« Autre taille »). */
  label: string;
  choices: readonly string[];
  value: string;
  onChange: (value: string) => void;
}

/**
 * Liste rapide en pastilles compactes (design-system § 7.4) ; « Autre » ouvre une saisie libre.
 * Une valeur hors liste (déjà saisie) rouvre directement la saisie libre.
 */
export function QuickPick({ label, choices, value, onChange }: QuickPickProps) {
  if (choices.includes(OTHER)) throw new Error(`QuickPick : « ${OTHER} » est réservé`);
  const inList = choices.includes(value);
  const [freeOpen, setFreeOpen] = useState(value !== "" && !inList);
  const free = freeOpen && !inList;
  const selected = inList ? value : free ? OTHER : null;
  const options = [
    ...choices.map((choice) => ({ value: choice, label: choice })),
    { value: OTHER, label: "Autre" },
  ];
  return (
    <div className="flex flex-col gap-2">
      <ChoiceChips
        compact
        label={label}
        options={options}
        value={selected}
        onChange={(next) => {
          if (next === OTHER) {
            setFreeOpen(true);
            if (inList) onChange("");
            return;
          }
          setFreeOpen(false);
          onChange(next);
        }}
      />
      {free && (
        <TextField
          label={`Autre ${label.toLocaleLowerCase("fr")}`}
          value={value}
          maxLength={64}
          onChange={(event) => {
            onChange(event.target.value);
          }}
        />
      )}
    </div>
  );
}
