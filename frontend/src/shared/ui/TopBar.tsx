import { ArrowLeft, Bell, ChevronDown, CircleUser } from "lucide-react";
import { FOCUS_OUTLINE, PRESS_TRANSITION, requireText } from "./controlClasses";
import { alertBadgeText, alertsLabel } from "./navigation";

export interface TopBarProps {
  /** Nom de la boutique (accueil) ou titre de l'écran (détail). */
  title: string;
  /** Plusieurs boutiques : le nom devient un bouton qui ouvre la liste (UC-SOC-03). */
  onTitleClick?: () => void;
  /** Écran de détail : flèche de retour (libellé accessible « Retour »). */
  onBack?: () => void;
  /** Nombre d'alertes non lues affiché sur la cloche. */
  alertCount: number;
  onAlertsClick: () => void;
  /** Accès « Mon compte » (§ 6.6, tous les rôles) : icône + mot « Compte », à droite de la cloche. */
  onAccountClick?: () => void;
}

const ICON_BUTTON =
  "inline-flex min-h-(--control-md) min-w-(--control-md) shrink-0 items-center " +
  `justify-center rounded-md text-primary hover:bg-primary-soft ${PRESS_TRANSITION} ${FOCUS_OUTLINE}`;

/** Bouton « Compte » : icône + mot ; le libellé accessible « Mon compte » contient le mot visible. */
const ACCOUNT_BUTTON =
  "inline-flex min-h-(--control-md) min-w-(--control-md) shrink-0 items-center gap-1 " +
  "rounded-md px-2 text-label font-semibold whitespace-nowrap text-primary hover:bg-primary-soft " +
  `${PRESS_TRANSITION} ${FOCUS_OUTLINE}`;

/**
 * Barre du haut (§ 6.6), 56 px. Retour et cloche sont les deux seules icônes sans mot
 * visible (exception de P5) : elles portent un libellé accessible. Le titre se tronque (« … »)
 * pour laisser la place aux boutons, même à 360 px.
 */
export function TopBar({
  title,
  onTitleClick,
  onBack,
  alertCount,
  onAlertsClick,
  onAccountClick,
}: TopBarProps) {
  requireText("TopBar", "title", title);
  if (!Number.isSafeInteger(alertCount) || alertCount < 0) {
    throw new Error(`TopBar : alertCount doit être un entier ≥ 0, reçu ${String(alertCount)}`);
  }
  return (
    <header className="flex min-h-(--control-lg) items-center gap-2 border-b border-border bg-surface px-2">
      {onBack !== undefined && (
        <button type="button" aria-label="Retour" onClick={onBack} className={ICON_BUTTON}>
          <ArrowLeft aria-hidden="true" className="size-6" />
        </button>
      )}
      {onTitleClick === undefined ? (
        <p className="m-0 min-w-0 flex-1 truncate px-2 text-title-sm font-semibold text-text">
          {title}
        </p>
      ) : (
        <button
          type="button"
          onClick={onTitleClick}
          className={
            "flex min-h-(--control-md) min-w-0 flex-1 items-center gap-1 rounded-md px-2 " +
            `text-left text-title-sm font-semibold text-text hover:bg-primary-soft ${PRESS_TRANSITION} ${FOCUS_OUTLINE}`
          }
        >
          <span className="truncate">{title}</span>
          <ChevronDown aria-hidden="true" className="size-6 shrink-0" />
        </button>
      )}
      <button
        type="button"
        aria-label={alertsLabel(alertCount)}
        onClick={onAlertsClick}
        className={`relative ${ICON_BUTTON}`}
      >
        <Bell aria-hidden="true" className="size-6" />
        {alertCount > 0 && (
          <span
            aria-hidden="true"
            className="absolute top-0 right-0 inline-flex min-h-6 min-w-6 items-center justify-center rounded-full bg-danger px-1 text-body font-bold text-on-primary tabular-nums"
          >
            {alertBadgeText(alertCount)}
          </span>
        )}
      </button>
      {onAccountClick !== undefined && (
        <button
          type="button"
          aria-label="Mon compte"
          onClick={onAccountClick}
          className={ACCOUNT_BUTTON}
        >
          <CircleUser aria-hidden="true" className="size-6 shrink-0" />
          <span>Compte</span>
        </button>
      )}
    </header>
  );
}
