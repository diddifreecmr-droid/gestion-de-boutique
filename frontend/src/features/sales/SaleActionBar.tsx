import type { ReactNode } from "react";
import { Check, RefreshCw, Send } from "lucide-react";
import { formatMoney } from "../../shared/format";
import { ActionBar, Badge, Button, type BadgeStatus } from "../../shared/ui";
import type { ApprovalView } from "./priceRequests/approvalView";
import {
  EXPIRED_TEXT,
  ONE_ARTICLE_TEXT,
  PENDING_TEXT,
  REFUSED_TEXT,
} from "./priceRequests/priceRequestText";

export interface SaleActionBarProps {
  total: number;
  /** Nombre de lignes : « 2 articles · Total » dès deux lignes (§ 7.4). */
  lineCount?: number;
  /** Accord du propriétaire pour un prix sous le minimum (UC-VEN-03). */
  approval: ApprovalView;
  submitting: boolean;
  onSubmit: () => void;
  onRequestApproval: () => void;
  onRefreshApproval: () => void;
}

const ASK_LABEL = "Demander l'accord du propriétaire";

function Status({ badge, word, children }: { badge: BadgeStatus; word: string; children: string }) {
  return (
    <p className="m-0 flex flex-wrap items-center gap-2 text-body text-text" aria-live="polite">
      <Badge status={badge}>{word}</Badge>
      <span>{children}</span>
    </p>
  );
}

/**
 * Total et action principale, en bas de l'écran (§ 6.1, § 7.1). La barre reste au-dessus
 * de la barre de navigation (`sticky`), dans le flux de la page. Sous le minimum, « Valider »
 * devient « Demander l'accord du propriétaire » (§ 6.1, variante métier), puis l'état suit.
 */
export function SaleActionBar(props: SaleActionBarProps) {
  const { total, approval, submitting, onSubmit, onRequestApproval, onRefreshApproval } = props;
  const lineCount = props.lineCount ?? 1;
  const validate = (reason?: string) => (
    <Button
      size="lg"
      fullWidth
      icon={Check}
      loading={submitting}
      onClick={onSubmit}
      {...(reason === undefined ? {} : { disabledReason: reason })}
    >
      Valider la vente
    </Button>
  );
  let content: ReactNode;
  switch (approval.kind) {
    case "none":
      content = validate();
      break;
    case "several":
      content = validate(ONE_ARTICLE_TEXT);
      break;
    case "ask":
    case "sending":
      content = (
        <>
          {approval.kind === "ask" && approval.again && (
            <Status badge="danger" word="Expirée">
              {EXPIRED_TEXT}
            </Status>
          )}
          <Button
            variant="secondary"
            size="lg"
            fullWidth
            icon={Send}
            loading={approval.kind === "sending"}
            onClick={onRequestApproval}
          >
            {ASK_LABEL}
          </Button>
        </>
      );
      break;
    case "pending":
      content = (
        <>
          <Status badge="warning" word="En attente">
            {`${PENDING_TEXT} — expire dans ${approval.remaining}.`}
          </Status>
          <Button variant="ghost" icon={RefreshCw} onClick={onRefreshApproval}>
            Actualiser l'état de la demande
          </Button>
          {validate("En attente de l'accord du propriétaire, ou changez le prix")}
        </>
      );
      break;
    case "accepted":
      content = (
        <>
          <Status badge="success" word="Accordé">
            {`Le propriétaire a accepté ce prix — accord valable encore ${approval.remaining}.`}
          </Status>
          {validate()}
        </>
      );
      break;
    case "refused":
      content = (
        <>
          <Status badge="danger" word="Refusée">
            {REFUSED_TEXT}
          </Status>
          {validate("Changez le prix : le propriétaire a refusé celui-ci")}
        </>
      );
      break;
  }
  const summary = (
    <p className="m-0 flex items-baseline justify-between gap-4">
      <span>
        {lineCount > 1 ? `${String(lineCount)} articles · ` : ""}
        Total
      </span>
      <strong className="text-amount tabular-nums">{formatMoney(total)}</strong>
    </p>
  );
  return (
    <div className="sticky bottom-16 z-20 -mx-4">
      <ActionBar fixed={false} summary={summary}>
        {content}
      </ActionBar>
    </div>
  );
}
