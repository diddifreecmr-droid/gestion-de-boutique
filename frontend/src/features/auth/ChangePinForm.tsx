import { useState, type FormEvent } from "react";
import { KeyRound } from "lucide-react";
import { useSession } from "../../core/services/servicesContext";
import { Button, TextField } from "../../shared/ui";
import { changePinError, type ChangePinField } from "./changePinErrors";
import { FormAlert } from "./FormAlert";
import { useSubmit } from "./useSubmit";
import { hasErrors, secretError, type FieldErrors, type SecretKind } from "./validation";

const LABELS: Record<SecretKind, Record<ChangePinField, string>> = {
  pin: {
    current: "Code actuel",
    next: "Nouveau code",
    confirmation: "Nouveau code, encore une fois",
  },
  password: {
    current: "Mot de passe actuel",
    next: "Nouveau mot de passe",
    confirmation: "Nouveau mot de passe, encore une fois",
  },
};

export interface ChangePinFormProps {
  kind: SecretKind;
  onDone: () => void;
}

/** UC-SOC-07 : code actuel puis deux fois le nouveau. Les codes trop simples sont refusés. */
export function ChangePinForm({ kind, onDone }: ChangePinFormProps) {
  const session = useSession();
  const [values, setValues] = useState<Record<ChangePinField, string>>({
    current: "",
    next: "",
    confirmation: "",
  });
  const [errors, setErrors] = useState<FieldErrors<ChangePinField>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const { pending, run } = useSubmit((error) => {
    const { field, message } = changePinError(error, kind);
    if (field === undefined) setFormError(message);
    else setErrors({ [field]: message });
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const found: FieldErrors<ChangePinField> = {
      current: secretError(kind, values.current),
      next: secretError(kind, values.next),
      confirmation:
        values.confirmation === values.next
          ? undefined
          : "Les deux saisies du nouveau code diffèrent",
    };
    setErrors(found);
    setFormError(null);
    if (hasErrors(found)) return;
    void run(async () => {
      await session.changePin({
        current_pin: values.current,
        new_pin: values.next,
        new_pin_confirmation: values.confirmation,
      });
      onDone();
    });
  };

  const fields: ChangePinField[] = ["current", "next", "confirmation"];
  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-4">
      {fields.map((field) => (
        <TextField
          key={field}
          label={LABELS[kind][field]}
          hint={
            field === "next" && kind === "pin" ? "6 chiffres, ni suite ni répétition" : undefined
          }
          type="password"
          autoComplete={field === "current" ? "current-password" : "new-password"}
          {...(kind === "pin" ? { inputMode: "numeric", maxLength: 6 } : {})}
          value={values[field]}
          error={errors[field]}
          onChange={(event) => {
            setValues((current) => ({ ...current, [field]: event.target.value }));
          }}
        />
      ))}
      <FormAlert message={formError} />
      <Button type="submit" size="lg" fullWidth icon={KeyRound} loading={pending}>
        {kind === "pin" ? "Changer mon code" : "Changer mon mot de passe"}
      </Button>
    </form>
  );
}
