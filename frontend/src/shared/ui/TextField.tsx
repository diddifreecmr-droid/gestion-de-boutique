import type { InputHTMLAttributes } from "react";
import { Field } from "./Field";
import { FIELD_INPUT, fieldFrameClasses } from "./controlClasses";

type NativeProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "className" | "style" | "id" | "aria-describedby" | "aria-invalid" | "children"
>;

export interface TextFieldProps extends NativeProps {
  label: string;
  hint?: string | undefined;
  error?: string | undefined;
  id?: string | undefined;
}

/** Champ texte (§ 6.2) : libellé au-dessus, 48 px, bordure 2 px primary au focus. */
export function TextField({ label, hint, error, id, type = "text", ...rest }: TextFieldProps) {
  return (
    <Field label={label} hint={hint} error={error} id={id}>
      {(control) => (
        <div className={fieldFrameClasses(error !== undefined)}>
          <input {...rest} {...control} type={type} className={FIELD_INPUT} />
        </div>
      )}
    </Field>
  );
}
