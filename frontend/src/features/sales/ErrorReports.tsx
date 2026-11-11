import { useId, useState } from "react";
import { Flag, Send } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import { useGateways } from "../../core/gateways/gateways";
import type { ErrorReport } from "../../core/gateways/salesContract";
import { formatDate, formatTime } from "../../shared/format";
import { Badge, Button, TextField } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { asError } from "./asError";
import { actionErrorMessage } from "./saleErrorMessage";

export const DESCRIPTION_REQUIRED = "Décrivez le problème";

function ReportItem({ report }: { report: ErrorReport }) {
  return (
    <li className="flex flex-col gap-1 rounded-lg bg-surface p-4 shadow-card">
      <p className="m-0 text-body text-text-muted">
        Signalé le {formatDate(report.reported_at)} à {formatTime(report.reported_at)}
      </p>
      <p className="m-0 break-words text-body text-text">« {report.description} »</p>
      {report.owner_reply === null ? (
        <p className="m-0">
          <Badge status="warning">En attente de réponse</Badge>
        </p>
      ) : (
        <p className="m-0 break-words text-body text-text">
          Réponse du propriétaire : {report.owner_reply}
        </p>
      )}
    </li>
  );
}

export interface ErrorReportsProps {
  shopId: string;
  saleId: string;
  reports: readonly ErrorReport[];
  /** Le vendeur peut signaler une erreur sur ses ventes (UC-VEN-06). */
  canReport: boolean;
  onReported: (report: ErrorReport) => void;
}

/** Erreurs signalées sur la vente et suite donnée ; formulaire « Signaler une erreur ». */
export function ErrorReports({
  shopId,
  saleId,
  reports,
  canReport,
  onReported,
}: ErrorReportsProps) {
  const { sales } = useGateways();
  const titleId = useId();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [reportId, setReportId] = useState(uuidV7);
  const [error, setError] = useState<string | undefined>();
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  if (reports.length === 0 && !canReport) return null;

  const send = async () => {
    if (text.trim() === "") {
      setError(DESCRIPTION_REQUIRED);
      return;
    }
    setError(undefined);
    setMessage(null);
    setBusy(true);
    try {
      onReported(
        await sales.reportError(shopId, saleId, { id: reportId, description: text.trim() }),
      );
      setOpen(false);
      setText("");
      setReportId(uuidV7());
    } catch (failure) {
      try {
        setMessage(actionErrorMessage(failure, "Signalement"));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-4">
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Erreurs signalées
      </h2>
      {reports.length > 0 && (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {reports.map((report) => (
            <ReportItem key={report.id} report={report} />
          ))}
        </ul>
      )}
      {canReport && !open && (
        <Button
          variant="secondary"
          icon={Flag}
          fullWidth
          onClick={() => {
            setOpen(true);
          }}
        >
          Signaler une erreur
        </Button>
      )}
      {canReport && open && (
        <>
          <TextField
            label="Quel est le problème ?"
            hint="Ex. mauvais prix, c'était 750 000"
            value={text}
            error={error}
            onChange={(event) => {
              setText(event.target.value);
            }}
          />
          {message !== null && <FormMessage text={message} />}
          <Button icon={Send} fullWidth loading={busy} onClick={() => void send()}>
            Envoyer au propriétaire
          </Button>
        </>
      )}
    </section>
  );
}
