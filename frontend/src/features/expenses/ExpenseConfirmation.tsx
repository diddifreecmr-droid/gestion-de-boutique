import { useEffect, useRef } from "react";
import { CheckCircle2, CirclePlus, List } from "lucide-react";
import type { Expense } from "../../core/gateways/expensesContract";
import { formatMoney } from "../../shared/format";
import { ActionBar, Button } from "../../shared/ui";

export interface ExpenseConfirmationProps {
  expense: Expense;
  onNew: () => void;
  onList: () => void;
}

/** Confirmation (UC-DEP-01) : « Dépense enregistrée — D-000012 » et « Nouvelle dépense ». */
export function ExpenseConfirmation({ expense, onNew, onList }: ExpenseConfirmationProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    headingRef.current?.focus();
  }, []);
  return (
    <>
      <div className="flex flex-col gap-2">
        <CheckCircle2 aria-hidden="true" className="size-8 text-success-text" />
        <h1
          ref={headingRef}
          tabIndex={-1}
          className="m-0 text-title font-bold text-text outline-hidden"
        >
          Dépense enregistrée — <span className="font-mono">{expense.number}</span>
        </h1>
      </div>
      <p className="m-0 flex items-baseline justify-between gap-4 rounded-lg bg-surface p-4 text-lead shadow-card">
        <span>Montant</span>
        <strong className="text-amount tabular-nums">{formatMoney(expense.amount)}</strong>
      </p>
      <Button variant="secondary" icon={List} fullWidth onClick={onList}>
        Voir les dépenses
      </Button>
      <div className="sticky bottom-16 z-20 -mx-4">
        <ActionBar fixed={false}>
          <Button size="lg" fullWidth icon={CirclePlus} onClick={onNew}>
            Nouvelle dépense
          </Button>
        </ActionBar>
      </div>
    </>
  );
}
