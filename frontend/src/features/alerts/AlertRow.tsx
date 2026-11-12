import { Check, ExternalLink } from "lucide-react";
import type { Alert } from "../../core/gateways/alertsContract";
import { formatDate, formatTime } from "../../shared/format";
import { Badge, Button } from "../../shared/ui";
import { alertTypeLabel } from "./alertText";

export interface AlertRowProps {
  alert: Alert;
  /** Lue ici même (avant la relecture du serveur). */
  read: boolean;
  busy: boolean;
  /** Adresse de l'élément lié, ou `null` (rien à ouvrir pour ce rôle). */
  link: string | null;
  onOpen: () => void;
  onMarkRead: () => void;
}

/**
 * Une alerte : type, message, date ; « Nouvelle » tant qu'elle n'est pas traitée, « Résolue »
 * si sa cause a disparu. Deux actions distinctes (jamais de bouton dans un bouton) : ouvrir
 * l'élément lié, marquer traitée.
 */
export function AlertRow({ alert, read, busy, link, onOpen, onMarkRead }: AlertRowProps) {
  const at = `${formatDate(alert.created_at)} à ${formatTime(alert.created_at)}`;
  return (
    <li className="flex flex-col gap-2 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={read ? "text-lead text-text-muted" : "text-lead font-bold text-text"}>
          {alertTypeLabel(alert.type)}
        </span>
        {!read && <Badge status="warning">Nouvelle</Badge>}
        {!alert.active && <Badge status="success">Résolue</Badge>}
      </div>
      <p className="m-0 break-words text-body text-text">{alert.message}</p>
      <p className="m-0 text-body text-text-muted">{at}</p>
      <div className="flex flex-wrap gap-2">
        {link !== null && (
          <Button variant="secondary" icon={ExternalLink} onClick={onOpen} loading={busy}>
            Ouvrir
          </Button>
        )}
        {!read && (
          <Button variant="ghost" icon={Check} onClick={onMarkRead} loading={busy}>
            Marquer traitée
          </Button>
        )}
      </div>
    </li>
  );
}
