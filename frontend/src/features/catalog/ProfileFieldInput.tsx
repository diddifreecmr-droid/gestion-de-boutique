import type { ProfileFieldResponse } from "../../core/gateways/catalogAdminContract";
import { ChoiceChips, TextField } from "../../shared/ui";
import { fieldKind } from "./fieldValues";
import { InlineMessage } from "./InlineMessage";
import { choiceLabel } from "./textileFields";

export interface ProfileFieldInputProps {
  spec: ProfileFieldResponse;
  value: string;
  error: string | undefined;
  onChange: (value: string) => void;
}

const YES_NO = [
  { value: "true", label: "Oui" },
  { value: "false", label: "Non" },
] as const;

/** Un champ d'article décrit par le profil : texte, nombre, Oui/Non ou liste de choix. */
export function ProfileFieldInput({ spec, value, error, onChange }: ProfileFieldInputProps) {
  const kind = fieldKind(spec);
  if (kind === "boolean" || kind === "choice") {
    const options =
      kind === "boolean"
        ? YES_NO
        : spec.choices.map((choice) => ({ value: choice, label: choiceLabel(spec, choice) }));
    return (
      <div className="flex flex-col gap-2">
        <ChoiceChips
          label={spec.label}
          options={options}
          value={value === "" ? null : value}
          onChange={onChange}
        />
        {error !== undefined && <InlineMessage text={error} />}
      </div>
    );
  }
  const numeric = kind === "integer" || kind === "decimal";
  return (
    <TextField
      label={spec.label}
      value={value}
      error={error}
      aria-required={spec.required}
      autoComplete="off"
      {...(numeric ? { inputMode: kind === "integer" ? "numeric" : "decimal" } : {})}
      onChange={(event) => {
        onChange(event.target.value);
      }}
    />
  );
}
