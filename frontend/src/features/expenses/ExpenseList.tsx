import { useState } from "react";
import { ChevronDown, CirclePlus, Receipt, Settings } from "lucide-react";
import type { Expense } from "../../core/gateways/expensesContract";
import { useExpensesDeps } from "../../core/gateways/httpExpenses";
import { formatDate } from "../../shared/format";
import { Button, EmptyState, KpiCard, Skeleton } from "../../shared/ui";
import { businessDate } from "./businessDay";
import { CategoryBars } from "./CategoryBars";
import { expenseErrorMessage } from "./expenseErrors";
import { ExpenseFiltersPanel } from "./ExpenseFiltersPanel";
import type { ScreenProps } from "./expenseNav";
import { ExpenseRow } from "./ExpenseRow";
import { defaultFilters, periodProblem, toQuery, type ListFilters } from "./filters";
import { FormMessage } from "./FormMessage";
import { asError, useLoad } from "./useLoad";

const countText = (count: number) =>
  count === 0 ? "Aucune dépense" : count === 1 ? "1 dépense" : `${String(count)} dépenses`;

/** Titre du total : « Dépenses du jour », « Dépenses du 01/11/2026 au 11/11/2026 ». */
function periodTitle(first: string, last: string, today: string): string {
  if (first !== last) return `Dépenses du ${formatDate(first)} au ${formatDate(last)}`;
  return first === today ? "Dépenses du jour" : `Dépenses du ${formatDate(first)}`;
}

/**
 * Liste des dépenses (UC-DEP-03) : jour par défaut, total de la période en haut (annulées
 * exclues, calculé par le serveur), répartition par catégorie, filtres, puis les lignes.
 */
export function ExpenseList({ shopId, refs, nav }: ScreenProps) {
  const { gateway, now } = useExpensesDeps();
  const today = businessDate(now());
  const [filters, setFilters] = useState<ListFilters>(() => defaultFilters(today));
  const [more, setMore] = useState<{ key: string; items: Expense[]; cursor: string | null }>();
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const valid = periodProblem(filters) === undefined;
  const query = valid ? toQuery(filters, today) : null;
  const key = JSON.stringify(query);
  const page = useLoad(key, () =>
    query === null ? Promise.resolve(null) : gateway.list(shopId, query),
  );
  const ready = page.status === "ready" ? page.value : null;
  const extra = more?.key === key ? more : undefined;
  const items = ready === null ? [] : [...ready.items, ...(extra?.items ?? [])];
  const cursor = extra === undefined ? (ready?.next_cursor ?? null) : extra.cursor;

  const loadMore = async () => {
    if (query === null || cursor === null) return;
    setMessage(null);
    try {
      const next = await gateway.list(shopId, query, cursor);
      setMore({ key, items: [...(extra?.items ?? []), ...next.items], cursor: next.next_cursor });
    } catch (error) {
      try {
        setMessage(expenseErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    }
  };

  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">Dépenses</h1>
      <Button
        size="lg"
        fullWidth
        icon={CirclePlus}
        onClick={() => {
          nav.create();
        }}
      >
        Nouvelle dépense
      </Button>
      {refs.me.role === "owner" && (
        <Button variant="ghost" icon={Settings} onClick={nav.settings}>
          Catégories et tags
        </Button>
      )}
      <ExpenseFiltersPanel
        shopId={shopId}
        refs={refs}
        value={filters}
        onChange={(patch) => {
          setFilters((current) => ({ ...current, ...patch }));
        }}
      />
      {page.status === "loading" && <Skeleton lines={4} label="Chargement des dépenses…" />}
      {page.status === "offline" && (
        <EmptyState message="Connexion nécessaire pour afficher les dépenses." />
      )}
      {ready !== null && (
        <>
          <KpiCard
            label={`Total — ${periodTitle(ready.first_day, ready.last_day, today)}`}
            amount={ready.totals.amount}
            detail={`${countText(ready.totals.count)} (annulées non comptées)`}
          />
          <CategoryBars refs={refs} totals={ready.totals} />
          {items.length === 0 ? (
            <EmptyState icon={Receipt} message="Aucune dépense sur cette période." />
          ) : (
            <ul
              aria-label="Liste des dépenses"
              className="m-0 list-none divide-y divide-border overflow-hidden rounded-lg bg-surface p-0 shadow-card"
            >
              {items.map((expense) => (
                <ExpenseRow key={expense.id} refs={refs} expense={expense} />
              ))}
            </ul>
          )}
          {message !== null && <FormMessage text={message} />}
          {cursor !== null && (
            <Button
              variant="secondary"
              icon={ChevronDown}
              fullWidth
              onClick={() => void loadMore()}
            >
              Voir plus
            </Button>
          )}
        </>
      )}
    </>
  );
}
