import { useState, type FormEvent } from "react";
import { LogIn } from "lucide-react";
import { ApiError } from "../../core/api/errors";
import { useSession } from "../../core/services/servicesContext";
import { Button, TextField } from "../../shared/ui";
import { commonAuthError, fallbackMessage, validationField } from "./authErrors";
import { FormAlert } from "./FormAlert";
import { useSubmit } from "./useSubmit";
import {
  hasErrors,
  phoneError,
  secretError,
  type FieldErrors,
  type SecretKind,
} from "./validation";

type Field = "phone" | "secret";

const SECRET_LABELS: Record<SecretKind, { label: string; hint: string | undefined }> = {
  pin: { label: "Code secret", hint: "6 chiffres" },
  password: { label: "Mot de passe", hint: undefined },
};

/**
 * Connexion par téléphone + code à 6 chiffres (UC-SOC-02) ou + mot de passe (administrateur
 * plateforme). En cas d'échec, la saisie reste : un appui suffit pour renvoyer.
 */
export function LoginForm({ kind }: { kind: SecretKind }) {
  const session = useSession();
  const [phone, setPhone] = useState("");
  const [secret, setSecret] = useState("");
  const [errors, setErrors] = useState<FieldErrors<Field>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const { pending, run } = useSubmit((error) => {
    const common = commonAuthError(error);
    if (common !== null) {
      setFormError(common.message);
    } else if (error instanceof ApiError && error.status === 401) {
      setErrors({ secret: error.message }); // « Numéro ou code incorrect » (aucune fuite)
    } else if (validationField(error) === "phone") {
      setErrors({ phone: "Numéro de téléphone invalide" });
    } else {
      setFormError(fallbackMessage(error));
    }
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const found: FieldErrors<Field> = {
      phone: phoneError(phone),
      secret: secretError(kind, secret),
    };
    setErrors(found);
    setFormError(null);
    if (hasErrors(found)) return;
    void run(() => session.login({ phone: phone.trim(), secret, kind }));
  };

  const secretText = SECRET_LABELS[kind];
  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-4">
      <TextField
        label="Numéro de téléphone"
        type="tel"
        inputMode="tel"
        autoComplete="tel"
        value={phone}
        error={errors.phone}
        onChange={(event) => {
          setPhone(event.target.value);
        }}
      />
      <TextField
        label={secretText.label}
        hint={secretText.hint}
        type="password"
        autoComplete="current-password"
        {...(kind === "pin" ? { inputMode: "numeric", maxLength: 6 } : {})}
        value={secret}
        error={errors.secret}
        onChange={(event) => {
          setSecret(event.target.value);
        }}
      />
      <FormAlert message={formError} />
      <Button type="submit" size="lg" fullWidth icon={LogIn} loading={pending}>
        Se connecter
      </Button>
    </form>
  );
}
