import { ArrowLeft } from "lucide-react";
import { useExpensesDeps } from "../../core/gateways/httpExpenses";
import { formatDate } from "../../shared/format";
import { Button } from "../../shared/ui";
import { businessDate } from "./businessDay";
import { correctionOf } from "./correctionRule";
import { draftOf, patchBody } from "./draft";
import { ExpenseForm } from "./ExpenseForm";
import type { ScreenProps } from "./expenseNav";
import { LoadingOrOffline } from "./LoadingOrOffline";
import { useLoad } from "./useLoad";

/** Correction d'une dépense (UC-DEP-04) : `PATCH` des champs changés avec la `version` lue. */
export function EditExpense({ shopId, refs, nav, id }: ScreenProps & { id: string }) {
  const { gateway, now } = useExpensesDeps();
  const loaded = useLoad(`${shopId}:${id}`, () => gateway.get(shopId, id));
  if (loaded.status !== "ready") {
    return <LoadingOrOffline title="Modifier la dépense" status={loaded.status} />;
  }
  const expense = loaded.value;
  const back = (
    <Button
      variant="ghost"
      icon={ArrowLeft}
      onClick={() => {
        nav.open(id);
      }}
    >
      Retour à la fiche
    </Button>
  );
  const correction = correctionOf(expense, refs.me.role, refs.me.userId, now());
  if (!correction.allowed) {
    return (
      <>
        <h1 className="m-0 text-title font-bold text-text">Modifier la dépense</h1>
        <p className="m-0 text-body text-text">{correction.reason}</p>
        {back}
      </>
    );
  }
  return (
    <ExpenseForm
      shopId={shopId}
      refs={refs}
      title="Modifier la dépense"
      initial={draftOf(expense)}
      today={businessDate(now())}
      submitLabel="Enregistrer la correction"
      keepCategoryId={expense.category_id}
      intro={
        <>
          <p className="m-0 text-body text-text-muted">
            <span className="font-mono">{expense.number}</span> du {formatDate(expense.spent_on)}
          </p>
          {back}
        </>
      }
      onSubmit={async (draft) => {
        await gateway.correct(shopId, id, patchBody(draft, expense));
        nav.open(id);
      }}
    />
  );
}
