import { ArrowLeft } from "lucide-react";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import type { StatementLine } from "../../core/gateways/receivablesContract";
import { formatDate, formatMoney, MINUS } from "../../shared/format";
import { Badge, Button, SummaryCard } from "../../shared/ui";
import { LoadingOrOffline } from "../expenses/LoadingOrOffline";
import { useLoad } from "../expenses/useLoad";
import { statementKind } from "./labels";
import type { ScreenProps } from "./receivablesNav";

const ADDS = new Set(["sale", "opening"]);

/** Montant signé : « + 800 000 FCFA » ajoute au dû, « − 200 000 FCFA » le réduit. */
function signed(line: StatementLine): string {
  return `${ADDS.has(line.kind) ? "+" : MINUS} ${formatMoney(line.amount)}`;
}

function Line({ line }: { line: StatementLine }) {
  const struck = line.cancelled ? "text-text-muted line-through" : "";
  const number = line.number === null ? "" : ` ${line.number}`;
  return (
    <li className="flex flex-col gap-1 px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <span className={`min-w-0 text-lead break-words text-text ${struck}`}>
          {statementKind(line.kind)}
          {number}
        </span>
        <span className={`shrink-0 text-lead font-semibold tabular-nums text-text ${struck}`}>
          {signed(line)}
        </span>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-body text-text-muted">{formatDate(line.on)}</span>
        {line.cancelled ? (
          <Badge status="danger">Annulé</Badge>
        ) : (
          <span className="text-body text-credit-text">
            Reste après : <span className="tabular-nums">{formatMoney(line.balance_after)}</span>
          </span>
        )}
      </div>
    </li>
  );
}

/** Relevé d'un client (UC-CRE-05) : total dû puis chaque opération et le reste après elle. */
export function CustomerStatement({
  shopId,
  nav,
  customerId,
}: ScreenProps & { customerId: string }) {
  const { gateway } = useReceivablesDeps();
  const loaded = useLoad(customerId, () => gateway.statement(shopId, customerId));
  if (loaded.status !== "ready") {
    return <LoadingOrOffline title="Relevé du client" status={loaded.status} />;
  }
  const { customer, lines, total_due: due } = loaded.value;
  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
        Retour aux créances
      </Button>
      <h1 className="m-0 text-title font-bold break-words text-text">Relevé de {customer.name}</h1>
      <p className="m-0 text-body text-text-muted">{customer.phone}</p>
      <SummaryCard lines={[]} due={due} dueLabel="Total dû" />
      {lines.length === 0 ? (
        <p className="m-0 text-body text-text-muted">Aucune opération à crédit.</p>
      ) : (
        <ol
          aria-label="Opérations du client"
          className="m-0 list-none divide-y divide-border rounded-lg bg-surface p-0 shadow-card"
        >
          {lines.map((line, index) => (
            <Line key={index} line={line} />
          ))}
        </ol>
      )}
    </>
  );
}
