import { AlertCircle } from "lucide-react";

/** Erreur du formulaire entier (blocage, réseau…), annoncée dès qu'elle apparaît. */
export function FormAlert({ message }: { message: string | null }) {
  return (
    <div aria-live="assertive">
      {message !== null && (
        <p role="alert" className="m-0 flex items-start gap-2 text-body text-danger-text">
          <AlertCircle aria-hidden="true" className="size-6 shrink-0" />
          <span>{message}</span>
        </p>
      )}
    </div>
  );
}
