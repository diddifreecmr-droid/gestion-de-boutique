import { useId, type ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { requireText } from "./controlClasses";

/** Attributs à poser sur le contrôle rendu par un Field (le lien libellé/aide/erreur). */
export interface FieldControlProps {
  id: string;
  "aria-describedby": string | undefined;
  "aria-invalid": true | undefined;
}

export interface FieldProps {
  /** Libellé toujours visible au-dessus du champ (§ 6.2), relié par `htmlFor`. */
  label: string;
  /** Aide courte sous le libellé, en text-muted. */
  hint?: string | undefined;
  /** Message d'erreur clair (« Le prix est vide ») ; sa présence met le champ en erreur. */
  error?: string | undefined;
  /** Identifiants supplémentaires à ajouter à aria-describedby (ex. suffixe « FCFA »). */
  describedBy?: string | undefined;
  /** Contenu affiché sous le contrôle (ex. « Stock disponible : 4 »). */
  footer?: ReactNode | undefined;
  id?: string | undefined;
  /**
   * Libellé à gauche du contrôle, sur la même ligne (contrôle compact : QuantityStepper) ;
   * l'aide passe sous la ligne. Faux par défaut : libellé au-dessus.
   */
  inline?: boolean;
  children: (control: FieldControlProps) => ReactNode;
}

/**
 * Enveloppe commune des champs (§ 6.2, § 8) : libellé au-dessus relié au contrôle, aide,
 * et zone d'erreur `aria-live="polite"` toujours présente pour que l'apparition d'une
 * erreur soit annoncée. L'erreur porte l'icône AlertCircle en plus du texte (P7).
 */
export function Field({
  label,
  hint,
  error,
  describedBy,
  footer,
  id,
  inline = false,
  children,
}: FieldProps) {
  const generatedId = useId();
  requireText("Field", "label", label);
  if (error?.trim() === "") {
    throw new Error("Field : error ne peut pas être vide (retirez-la ou écrivez un message)");
  }
  const controlId = id ?? generatedId;
  const hintId = `${controlId}-hint`;
  const errorId = `${controlId}-error`;
  const invalid = error !== undefined;
  const ids = [hint === undefined ? "" : hintId, describedBy ?? "", invalid ? errorId : ""]
    .filter((value) => value !== "")
    .join(" ");

  const labelElement = (
    <label htmlFor={controlId} className="text-label font-semibold text-text">
      {label}
    </label>
  );
  const hintElement = hint !== undefined && (
    <p id={hintId} className="m-0 text-body text-text-muted">
      {hint}
    </p>
  );
  const control = children({
    id: controlId,
    "aria-describedby": ids === "" ? undefined : ids,
    "aria-invalid": invalid || undefined,
  });

  return (
    <div className="flex flex-col gap-2">
      {inline ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
            {labelElement}
            {control}
          </div>
          {hintElement}
        </>
      ) : (
        <>
          {labelElement}
          {hintElement}
          {control}
        </>
      )}
      {footer}
      <div aria-live="polite">
        {invalid && (
          <p id={errorId} className="m-0 flex items-start gap-1 text-body text-danger-text">
            <AlertCircle aria-hidden="true" className="size-6 shrink-0" />
            <span>{error}</span>
          </p>
        )}
      </div>
    </div>
  );
}
