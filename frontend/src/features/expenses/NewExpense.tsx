import { useState } from "react";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import type { Expense } from "../../core/gateways/expensesContract";
import { useExpensesDeps } from "../../core/gateways/httpExpenses";
import { Button, EmptyState, Skeleton } from "../../shared/ui";
import { businessDate } from "./businessDay";
import { createBody, emptyDraft, repeatedDraft, type Draft } from "./draft";
import { ExpenseConfirmation } from "./ExpenseConfirmation";
import { ExpenseForm } from "./ExpenseForm";
import type { ScreenProps } from "./expenseNav";
import { useLoad } from "./useLoad";

export interface NewExpenseProps extends ScreenProps {
  /** « Refaire cette dépense » : identifiant de la dépense à reprendre (UC-DEP-05). */
  repeatOf?: string | undefined;
}

/** « Nouvelle dépense » (UC-DEP-01), vierge ou pré-remplie par `GET /expenses/{id}/repeat`. */
export function NewExpense({ shopId, refs, nav, repeatOf }: NewExpenseProps) {
  const { gateway, now } = useExpensesDeps();
  const [round, setRound] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [recorded, setRecorded] = useState<Expense | null>(null);
  /** Un identifiant par saisie : renvoyer après une coupure ne crée pas de doublon (§ 6.1). */
  const [clientId, setClientId] = useState(uuidV7);
  const today = businessDate(now());
  const source = useLoad(`${repeatOf ?? ""}:${String(attempt)}`, () =>
    repeatOf === undefined ? Promise.resolve(null) : gateway.repeat(shopId, repeatOf),
  );

  if (recorded !== null) {
    return (
      <ExpenseConfirmation
        expense={recorded}
        onNew={() => {
          setRecorded(null);
          setClientId(uuidV7());
          setRound((n) => n + 1);
          if (repeatOf !== undefined) nav.create();
        }}
        onList={nav.list}
      />
    );
  }
  if (source.status !== "ready") {
    return (
      <>
        <h1 className="m-0 text-title font-bold text-text">Nouvelle dépense</h1>
        {source.status === "loading" ? (
          <Skeleton lines={4} label="Préparation de la dépense…" />
        ) : (
          <EmptyState
            message="Connexion nécessaire pour reprendre cette dépense."
            action={
              <Button
                variant="secondary"
                icon={RefreshCw}
                onClick={() => {
                  setAttempt((n) => n + 1);
                }}
              >
                Réessayer
              </Button>
            }
          />
        )}
      </>
    );
  }
  const initial: Draft =
    source.value === null ? emptyDraft(refs, today) : repeatedDraft(refs, today, source.value);
  return (
    <ExpenseForm
      key={round}
      shopId={shopId}
      refs={refs}
      title="Nouvelle dépense"
      initial={initial}
      today={today}
      submitLabel="Valider la dépense"
      intro={
        <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
          Retour aux dépenses
        </Button>
      }
      onSubmit={async (draft) => {
        setRecorded(await gateway.record(shopId, createBody(draft, clientId, today)));
      }}
    />
  );
}
