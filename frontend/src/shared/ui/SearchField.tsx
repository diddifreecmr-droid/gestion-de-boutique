import { useRef, type InputHTMLAttributes } from "react";
import { Search, X } from "lucide-react";
import { Field } from "./Field";
import { FIELD_INPUT, FOCUS_OUTLINE, fieldFrameClasses } from "./controlClasses";

type NativeProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  | "className"
  | "style"
  | "id"
  | "type"
  | "value"
  | "defaultValue"
  | "onChange"
  | "aria-describedby"
  | "aria-invalid"
  | "children"
>;

export interface SearchFieldProps extends NativeProps {
  label: string;
  value: string;
  /** Appelé à chaque lettre : les résultats s'affichent dès la première (§ 6.2). */
  onChange: (value: string) => void;
  /** Libellé du bouton qui vide le champ (icône + mot, P5). */
  clearLabel?: string;
  hint?: string | undefined;
  error?: string | undefined;
  id?: string | undefined;
}

/**
 * Champ de recherche (§ 6.2) : loupe, bouton « Effacer » quand il y a du texte (le focus
 * revient alors dans le champ). `type="text"` + `inputMode="search"` : pas de second
 * bouton d'effacement natif du navigateur.
 */
export function SearchField({
  label,
  value,
  onChange,
  clearLabel = "Effacer",
  hint,
  error,
  id,
  ...rest
}: SearchFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <Field label={label} hint={hint} error={error} id={id}>
      {(control) => (
        <div className={fieldFrameClasses(error !== undefined)}>
          <Search aria-hidden="true" className="size-6 shrink-0 text-text-muted" />
          <input
            {...rest}
            {...control}
            ref={inputRef}
            type="text"
            inputMode="search"
            enterKeyHint="search"
            autoComplete="off"
            value={value}
            onChange={(event) => {
              onChange(event.target.value);
            }}
            className={FIELD_INPUT}
          />
          {value !== "" && (
            <button
              type="button"
              onClick={() => {
                onChange("");
                inputRef.current?.focus();
              }}
              className={
                "-mr-2 inline-flex min-h-(--control-md) shrink-0 items-center gap-1 rounded-md " +
                `px-2 text-label font-semibold text-primary hover:bg-primary-soft ${FOCUS_OUTLINE}`
              }
            >
              <X aria-hidden="true" className="size-6 shrink-0" />
              <span>{clearLabel}</span>
            </button>
          )}
        </div>
      )}
    </Field>
  );
}
