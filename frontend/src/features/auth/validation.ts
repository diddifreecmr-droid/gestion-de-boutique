/** Contrôles de saisie avant envoi (le serveur reste juge : PIN_TOO_SIMPLE, etc.). */

/** Longueur minimale du mot de passe de l'administrateur plateforme (backend, § 15.1). */
export const PASSWORD_MIN_LENGTH = 10;
const PIN = /^\d{6}$/;

export function phoneError(value: string): string | undefined {
  return value.trim() === "" ? "Le numéro est vide" : undefined;
}

export function pinError(value: string): string | undefined {
  if (value === "") return "Le code est vide";
  return PIN.test(value) ? undefined : "Le code doit avoir 6 chiffres";
}

export function passwordError(value: string): string | undefined {
  if (value === "") return "Le mot de passe est vide";
  return value.length >= PASSWORD_MIN_LENGTH
    ? undefined
    : `Le mot de passe doit avoir au moins ${String(PASSWORD_MIN_LENGTH)} caractères`;
}

export type SecretKind = "pin" | "password";

export function secretError(kind: SecretKind, value: string): string | undefined {
  return kind === "pin" ? pinError(value) : passwordError(value);
}

/** Erreurs par champ : un formulaire n'est envoyé que si l'objet est vide. */
export type FieldErrors<K extends string> = { [P in K]?: string | undefined };

export function hasErrors<K extends string>(errors: FieldErrors<K>): boolean {
  return Object.values(errors).some((message) => message !== undefined);
}
