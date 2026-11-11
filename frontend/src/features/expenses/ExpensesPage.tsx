import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useSearchParams } from "react-router";
import type { Role } from "../../core/auth/me";
import { useExpensesDeps } from "../../core/gateways/httpExpenses";
import { useSignedIn } from "../../core/services/servicesContext";
import { Button, EmptyState, Skeleton } from "../../shared/ui";
import { EXPENSE_ROLES, VIEW, type ExpenseNav } from "./expenseNav";
import { ExpenseDetail } from "./ExpenseDetail";
import { ExpenseList } from "./ExpenseList";
import { ExpenseSettings } from "./ExpenseSettings";
import { NewExpense } from "./NewExpense";
import { EditExpense } from "./EditExpense";
import { loadReferences } from "./references";
import { useLoad } from "./useLoad";

export interface ExpensesPageProps {
  shopId: string;
  role: Role;
}

/**
 * Section « Dépenses » : liste, nouvelle dépense, fiche, correction, réglages. La vue est
 * dans l'adresse (`?vue=…&id=…`) : le bouton retour du téléphone revient à l'écran précédent.
 */
export function ExpensesPage({ shopId, role }: ExpensesPageProps) {
  if (!EXPENSE_ROLES.includes(role)) {
    throw new Error(`Le rôle « ${role} » n'accède pas aux dépenses (garde de route manquante)`);
  }
  const me = useSignedIn();
  const { gateway } = useExpensesDeps();
  const [params, setParams] = useSearchParams();
  const [round, setRound] = useState(0);
  /** Réglages modifiés : les référentiels sont relus en quittant les réglages. */
  const [stale, setStale] = useState(false);
  const view = params.get("vue");
  if (stale && view !== VIEW.settings) {
    setStale(false);
    setRound((n) => n + 1);
  }
  const refs = useLoad(`${shopId}:${String(round)}`, () =>
    loadReferences(gateway, shopId, { userId: me.userId, name: me.name, role }),
  );

  const nav: ExpenseNav = {
    list: () => {
      setParams({});
    },
    open: (id) => {
      setParams({ vue: VIEW.detail, id });
    },
    create: (repeatOf) => {
      setParams(
        repeatOf === undefined ? { vue: VIEW.create } : { vue: VIEW.create, refaire: repeatOf },
      );
    },
    edit: (id) => {
      setParams({ vue: VIEW.edit, id });
    },
    settings: () => {
      setParams({ vue: VIEW.settings });
    },
  };

  if (refs.status !== "ready") {
    return (
      <>
        <h1 className="m-0 text-title font-bold text-text">Dépenses</h1>
        {refs.status === "loading" ? (
          <Skeleton lines={4} label="Chargement des dépenses…" />
        ) : (
          <EmptyState
            message="Connexion nécessaire pour ouvrir les dépenses."
            action={
              <Button
                variant="secondary"
                icon={RefreshCw}
                onClick={() => {
                  setRound((n) => n + 1);
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

  const id = params.get("id");
  const common = { shopId, refs: refs.value, nav };
  if (view === VIEW.create) {
    const repeatOf = params.get("refaire") ?? undefined;
    return <NewExpense key={repeatOf ?? "new"} {...common} repeatOf={repeatOf} />;
  }
  if (view === VIEW.detail && id !== null) return <ExpenseDetail key={id} {...common} id={id} />;
  if (view === VIEW.edit && id !== null) return <EditExpense key={id} {...common} id={id} />;
  if (view === VIEW.settings && role === "owner") {
    return (
      <ExpenseSettings
        {...common}
        onChanged={() => {
          setStale(true);
        }}
      />
    );
  }
  return <ExpenseList {...common} />;
}
