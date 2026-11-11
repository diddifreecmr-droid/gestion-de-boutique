import { useId, useLayoutEffect, useRef, type ChangeEvent, type InputHTMLAttributes } from "react";
import { Field } from "./Field";
import { FIELD_INPUT, fieldFrameClasses } from "./controlClasses";
import { caretAfterDigits, digitsBefore, formatAmountInput, parseAmountInput } from "./amountInput";

type NativeProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  | "className"
  | "style"
  | "id"
  | "type"
  | "inputMode"
  | "value"
  | "defaultValue"
  | "onChange"
  | "aria-describedby"
  | "aria-invalid"
  | "children"
>;

export interface AmountFieldProps extends NativeProps {
  label: string;
  /** Montant en FCFA (entier positif) ou `null` si le champ est vide. Jamais NaN. */
  value: number | null;
  onChange: (value: number | null) => void;
  hint?: string | undefined;
  error?: string | undefined;
  id?: string | undefined;
}

/**
 * Champ de montant (§ 6.2) : clavier numérique, séparateur de milliers inséré pendant la
 * frappe (le curseur reste après le même chiffre), suffixe fixe « FCFA » relié au champ.
 */
export function AmountField({
  label,
  value,
  onChange,
  hint,
  error,
  id,
  ...rest
}: AmountFieldProps) {
  const suffixId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  /** Chiffres à laisser avant le curseur après le prochain rendu (null = ne rien faire). */
  const pendingCaret = useRef<number | null>(null);
  const display = formatAmountInput(value);

  useLayoutEffect(() => {
    const input = inputRef.current;
    const digits = pendingCaret.current;
    pendingCaret.current = null;
    if (input === null || digits === null || document.activeElement !== input) return;
    const position = caretAfterDigits(input.value, digits);
    input.setSelectionRange(position, position);
  });

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { value: raw, selectionStart } = event.target;
    const parsed = parseAmountInput(raw);
    if (!parsed.ok) return; // au-delà de 15 chiffres : la frappe est ignorée, le champ reste tel quel
    pendingCaret.current = digitsBefore(raw, selectionStart ?? raw.length);
    onChange(parsed.value);
  };

  return (
    <Field label={label} hint={hint} error={error} id={id} describedBy={suffixId}>
      {(control) => (
        <div className={fieldFrameClasses(error !== undefined)}>
          <input
            {...rest}
            {...control}
            ref={inputRef}
            type="text"
            inputMode="numeric"
            autoComplete="off"
            value={display}
            onChange={handleChange}
            className={`${FIELD_INPUT} text-lead font-bold tabular-nums`}
          />
          <span id={suffixId} className="shrink-0 text-body text-text-muted">
            FCFA
          </span>
        </div>
      )}
    </Field>
  );
}
