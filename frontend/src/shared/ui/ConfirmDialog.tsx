import { useId, useRef, useState, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Button } from "./Button";
import { TextField } from "./TextField";
import { requireText } from "./controlClasses";
import { useFocusTrap } from "./useFocusTrap";

export interface ConfirmDialogProps {
  open: boolean;
  /** « Annuler la vente V-000124 ? » */
  title: string;
  /** Conséquence, en clair. */
  children?: ReactNode;
  /** Libellé du bouton danger (« Annuler la vente »). */
  confirmLabel: string;
  confirmIcon?: LucideIcon;
  /** Libellé du bouton de sortie (« Retour » par défaut). */
  cancelLabel?: string;
  /** Exige un motif (annulation, passage en perte) : le bouton refuse un motif vide. */
  requireReason?: boolean;
  reasonLabel?: string;
  /** Reçoit le motif saisi (sans espaces autour), ou `null` si aucun motif n'est demandé. */
  onConfirm: (reason: string | null) => void;
  onCancel: () => void;
}

/** Message affiché quand le motif obligatoire est vide. */
export const REASON_REQUIRED = "Le motif est obligatoire";

/**
 * Confirmation d'une action destructrice (§ 6.5) : feuille du bas sur téléphone, fenêtre
 * centrée dès 600 px. Modale ARIA : focus piégé, Échap = Retour, focus rendu à la fermeture.
 * Le focus s'ouvre sur le motif s'il est demandé, sinon sur « Retour » (choix sans risque).
 */
export function ConfirmDialog(props: ConfirmDialogProps) {
  if (!props.open) return null;
  return <DialogSheet {...props} />;
}

function DialogSheet({
  title,
  children,
  confirmLabel,
  confirmIcon,
  cancelLabel = "Retour",
  requireReason = false,
  reasonLabel = "Motif",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  requireText("ConfirmDialog", "title", title);
  requireText("ConfirmDialog", "confirmLabel", confirmLabel);
  const titleId = useId();
  const messageId = useId();
  const reasonId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const cancelId = useId();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const onKeyDown = useFocusTrap(panelRef, true, onCancel, requireReason ? reasonId : cancelId);

  const confirm = () => {
    if (!requireReason) {
      onConfirm(null);
      return;
    }
    const trimmed = reason.trim();
    if (trimmed === "") {
      setError(REASON_REQUIRED);
      document.getElementById(reasonId)?.focus();
      return;
    }
    onConfirm(trimmed);
  };

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-text/50 sm:items-center sm:p-4">
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={children === undefined ? undefined : messageId}
        tabIndex={-1}
        onKeyDown={onKeyDown}
        className="safe-bottom-4 flex w-full max-w-150 flex-col gap-4 rounded-t-lg bg-surface px-4 pt-4 shadow-sheet sm:rounded-lg"
      >
        <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
          {title}
        </h2>
        {children !== undefined && (
          <div id={messageId} className="text-body text-text">
            {children}
          </div>
        )}
        {requireReason && (
          <TextField
            id={reasonId}
            label={reasonLabel}
            value={reason}
            error={error}
            onChange={(event) => {
              setReason(event.target.value);
              if (event.target.value.trim() !== "") setError(undefined);
            }}
          />
        )}
        <div className="grid grid-cols-2 gap-2">
          <Button id={cancelId} variant="secondary" fullWidth onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button
            variant="danger"
            fullWidth
            onClick={confirm}
            {...(confirmIcon === undefined ? {} : { icon: confirmIcon })}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
