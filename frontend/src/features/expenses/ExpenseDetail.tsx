import { useState } from "react";
import { ArrowLeft, Pencil, Repeat, XCircle } from "lucide-react";
import type { Expense } from "../../core/gateways/expensesContract";
import { useExpensesDeps } from "../../core/gateways/httpExpenses";
import { Badge, Button, ConfirmDialog } from "../../shared/ui";
import { correctionOf } from "./correctionRule";
import { expenseErrorMessage } from "./expenseErrors";
import type { ScreenProps } from "./expenseNav";
import { ExpenseFacts } from "./ExpenseFacts";
import { cancellationText } from "./expenseText";
import { FormMessage } from "./FormMessage";
import { LoadingOrOffline } from "./LoadingOrOffline";
import { asError, useLoad } from "./useLoad";

/** Fiche d'une dépense (UC-DEP-03 à 05) : corriger, annuler avec motif, refaire. */
export function ExpenseDetail({ shopId, refs, nav, id }: ScreenProps & { id: string }) {
  const { gateway, now } = useExpensesDeps();
  const loaded = useLoad(`${shopId}:${id}`, () => gateway.get(shopId, id));
  const [updated, setUpdated] = useState<Expense | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  if (loaded.status !== "ready") return <LoadingOrOffline title="Dépense" status={loaded.status} />;

  const expense = updated ?? loaded.value;
  const cancelled = expense.status === "cancelled";
  const correction = correctionOf(expense, refs.me.role, refs.me.userId, now());
  const reason = correction.allowed ? {} : { disabledReason: correction.reason };
  const mention = cancellationText(refs, expense);

  const cancel = async (text: string) => {
    setConfirming(false);
    setBusy(true);
    setMessage(null);
    try {
      setUpdated(await gateway.cancel(shopId, id, text));
    } catch (error) {
      try {
        setMessage(expenseErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
        Retour aux dépenses
      </Button>
      <div className="flex flex-col gap-2">
        <h1 className="m-0 text-title font-bold text-text">
          Dépense <span className="font-mono">{expense.number}</span>
        </h1>
        {cancelled && (
          <p className="m-0 flex flex-col items-start gap-2">
            <Badge status="danger">Annulée</Badge>
            <span className="text-body text-text">{mention}</span>
          </p>
        )}
      </div>
      <ExpenseFacts refs={refs} expense={expense} />
      {message !== null && <FormMessage text={message} />}
      {!cancelled && (
        <div className="flex flex-col gap-4">
          <Button
            variant="secondary"
            icon={Pencil}
            fullWidth
            onClick={() => {
              nav.edit(id);
            }}
            {...reason}
          >
            Modifier
          </Button>
          <Button
            variant="danger"
            icon={XCircle}
            fullWidth
            loading={busy}
            onClick={() => {
              setConfirming(true);
            }}
            {...reason}
          >
            Annuler la dépense
          </Button>
        </div>
      )}
      <Button
        variant="secondary"
        icon={Repeat}
        fullWidth
        onClick={() => {
          nav.create(id);
        }}
      >
        Refaire cette dépense
      </Button>
      <ConfirmDialog
        open={confirming}
        title={`Annuler la dépense ${expense.number} ?`}
        confirmLabel="Annuler la dépense"
        confirmIcon={XCircle}
        requireReason
        onConfirm={(text) => {
          if (text === null) throw new Error("Annulation sans motif : le dialogue l'exige");
          void cancel(text);
        }}
        onCancel={() => {
          setConfirming(false);
        }}
      >
        Elle restera visible, barrée, et ne comptera plus dans aucun total.
      </ConfirmDialog>
    </>
  );
}
