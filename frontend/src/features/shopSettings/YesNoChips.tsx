import { ChoiceChips } from "../../shared/ui";

const OPTIONS = [
  { value: "yes", label: "Oui" },
  { value: "no", label: "Non" },
] as const;

export interface YesNoChipsProps {
  label: string;
  value: boolean;
  onChange: (value: boolean) => void;
}

/** Choix Oui / Non en grosses pastilles (§ 6.2) : sert d'interrupteur, lisible sans couleur. */
export function YesNoChips({ label, value, onChange }: YesNoChipsProps) {
  return (
    <ChoiceChips
      label={label}
      options={OPTIONS}
      value={value ? "yes" : "no"}
      onChange={(choice) => {
        onChange(choice === "yes");
      }}
    />
  );
}
