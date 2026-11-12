import { useState } from "react";
import { Bell, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router";
import { ApiError } from "../../core/api/errors";
import type { Role } from "../../core/auth/me";
import type { Alert, AlertPage } from "../../core/gateways/alertsContract";
import { useAlertsGateway } from "../../core/gateways/httpAlerts";
import { Button, ChoiceChips, EmptyState, ListCard, Skeleton } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { asError } from "../expenses/useLoad";
import { entityLink } from "./alertLinks";
import { AlertRow } from "./AlertRow";
import { alertActionMessage, unreadText } from "./alertText";
import { MoreButton } from "./MoreButton";
import { usePagedList } from "./usePagedList";

type Shown = "unread" | "all";

const SHOWN = [
  { value: "unread", label: "Non lues" },
  { value: "all", label: "Toutes" },
] as const;

/**
 * Alertes de l'utilisateur dans la boutique active (UC-SOC-09) : les plus récentes en haut.
 * « Marquer traitée » appelle `POST /alerts/{id}/read` (ALR-01) ; « Ouvrir » la marque aussi
 * traitée puis ouvre l'élément lié (ALR-02). Chacun ne voit que les siennes (ALR-03, serveur).
 */
export function AlertsPage({ shopId, role }: { shopId: string; role: Role }) {
  const gateway = useAlertsGateway();
  const navigate = useNavigate();
  const [shown, setShown] = useState<Shown>("unread");
  const [readHere, setReadHere] = useState<ReadonlySet<string>>(new Set());
  const [unread, setUnread] = useState<number | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  const list = usePagedList<AlertPage, Alert>(`${shopId}|${shown}`, (cursor) =>
    gateway.list(shopId, { unreadOnly: shown === "unread", cursor }),
  );

  const markRead = async (alert: Alert, then?: string) => {
    setBusy(alert.id);
    setMessage(null);
    try {
      setUnread(await gateway.markRead(shopId, alert.id));
      setReadHere((current) => new Set(current).add(alert.id));
      if (then !== undefined) void navigate(then);
    } catch (error) {
      try {
        setMessage(alertActionMessage(error));
        if (error instanceof ApiError) list.reload(); // 404 : la liste a changé, on la relit
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(null);
    }
  };

  const first = list.first;
  const count = unread ?? (first.status === "ready" ? first.value.unread_count : null);
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Alertes</h1>
      {count !== null && <p className="m-0 text-body text-text-muted">{unreadText(count)}</p>}
      <ChoiceChips
        label="Afficher"
        options={SHOWN}
        value={shown}
        onChange={(value) => {
          setShown(value);
          setMessage(null);
        }}
      />
      {message !== null && <FormMessage text={message} />}
      {first.status === "loading" && <Skeleton lines={3} label="Chargement des alertes…" />}
      {first.status === "offline" && (
        <EmptyState
          message="Connexion nécessaire pour afficher les alertes."
          action={
            <Button variant="secondary" icon={RefreshCw} onClick={list.reload}>
              Réessayer
            </Button>
          }
        />
      )}
      {first.status === "ready" && list.items.length === 0 && (
        <EmptyState
          icon={Bell}
          message={
            shown === "unread" ? "Aucune alerte à traiter." : "Aucune alerte pour l'instant."
          }
        />
      )}
      {list.items.length > 0 && (
        <ListCard label="Liste des alertes">
          {list.items.map((alert) => {
            const link = entityLink(shopId, alert.entity, role);
            const read = alert.read || readHere.has(alert.id);
            return (
              <AlertRow
                key={alert.id}
                alert={alert}
                read={read}
                busy={busy === alert.id}
                link={link}
                onOpen={() => {
                  if (link === null) throw new Error("Alerte sans élément à ouvrir");
                  if (read) void navigate(link);
                  else void markRead(alert, link);
                }}
                onMarkRead={() => void markRead(alert)}
              />
            );
          })}
        </ListCard>
      )}
      <MoreButton list={list} />
    </>
  );
}
