import { useId } from "react";
import { FOCUS_OUTLINE, PRESS_TRANSITION, requireText } from "./controlClasses";

export interface SwitchProps {
  /** Nom de l'interrupteur (« Créances »), affiché à gauche et nom accessible. */
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  /** Phrase sous le libellé (dépendance, effet) en `text-muted`, reliée par `aria-describedby`. */
  hint?: string;
}

/**
 * Interrupteur marche / arrêt (design-system § 6.2) : toute la ligne (56 px) est la cible ;
 * piste `primary` quand il est activé, `border-strong` sinon, et le mot « Activé » ou
 * « Désactivé » écrit à côté (la couleur ne suffit jamais, P7). Motif ARIA « switch ».
 */
export function Switch({ label, checked, onChange, hint }: SwitchProps) {
  const hintId = useId();
  requireText("Switch", "label", label);
  const track = checked ? "bg-primary" : "bg-border-strong";
  const thumb = checked ? "translate-x-5" : "translate-x-0";
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      {...(hint === undefined ? {} : { "aria-describedby": hintId })}
      onClick={() => {
        onChange(!checked);
      }}
      className={
        "flex min-h-(--control-lg) w-full items-center gap-4 rounded-md border border-border " +
        `bg-surface px-4 py-2 text-left hover:bg-primary-soft ${PRESS_TRANSITION} ${FOCUS_OUTLINE}`
      }
    >
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-lead font-semibold text-text">{label}</span>
        {hint !== undefined && (
          <span id={hintId} className="text-body text-text-muted">
            {hint}
          </span>
        )}
      </span>
      <span className="text-label text-text-muted">{checked ? "Activé" : "Désactivé"}</span>
      <span
        aria-hidden="true"
        className={`flex h-7 w-12 shrink-0 items-center rounded-full p-1 ${PRESS_TRANSITION} ${track}`}
      >
        <span className={`size-5 rounded-full bg-surface shadow-card ${thumb}`} />
      </span>
    </button>
  );
}
