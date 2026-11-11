import { useState } from "react";
import { Plus } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import type { ExpenseCategory, ExpenseCategoryPatch } from "../../core/gateways/expensesContract";
import { useExpensesDeps } from "../../core/gateways/httpExpenses";
import { Button, Skeleton, TextField } from "../../shared/ui";
import { CategoryRow } from "./CategoryRow";
import { expenseErrorMessage } from "./expenseErrors";
import { FormMessage } from "./FormMessage";
import { asError, useLoad } from "./useLoad";

export interface CategorySettingsProps {
  shopId: string;
  onChanged: () => void;
}

/** Catégories de dépense (UC-DEP-02, propriétaire) : ajouter, renommer, désactiver. */
export function CategorySettings({ shopId, onChanged }: CategorySettingsProps) {
  const { gateway } = useExpensesDeps();
  const loaded = useLoad(shopId, () => gateway.categories(shopId));
  const [changed, setChanged] = useState<Record<string, ExpenseCategory>>({});
  const [added, setAdded] = useState<ExpenseCategory[]>([]);
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string | undefined>(undefined);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  if (loaded.status === "loading") return <Skeleton lines={3} label="Chargement des catégories…" />;
  if (loaded.status === "offline") return <FormMessage text="Connexion nécessaire." />;

  const categories = [...loaded.value, ...added]
    .map((category) => changed[category.id] ?? category)
    .sort((a, b) => a.display_order - b.display_order);

  /** Exécute un envoi ; `true` s'il a réussi, sinon le message est affiché. */
  const run = async (key: string, action: () => Promise<ExpenseCategory>, isNew: boolean) => {
    setBusy(key);
    setMessage(null);
    try {
      const result = await action();
      if (isNew) setAdded((current) => [...current, result]);
      else setChanged((current) => ({ ...current, [result.id]: result }));
      onChanged();
      return true;
    } catch (error) {
      try {
        setMessage(expenseErrorMessage(error));
      } catch (unexpected) {
        setFatal(unexpected);
      }
      return false;
    } finally {
      setBusy(null);
    }
  };

  const patch = (category: ExpenseCategory, change: Omit<ExpenseCategoryPatch, "version">) =>
    run(
      category.id,
      () => gateway.updateCategory(shopId, category.id, { ...change, version: category.version }),
      false,
    );

  const add = async () => {
    if (name.trim() === "") {
      setNameError("Le nom est vide");
      return;
    }
    if (await run("new", () => gateway.createCategory(shopId, uuidV7(), name.trim()), true)) {
      setName("");
    }
  };

  return (
    <section aria-labelledby="expense-categories" className="flex flex-col gap-4">
      <h2 id="expense-categories" className="m-0 text-title-sm font-semibold text-text">
        Catégories
      </h2>
      <ul
        aria-label="Catégories de dépense"
        className="m-0 list-none divide-y divide-border rounded-lg bg-surface p-0 shadow-card"
      >
        {categories.map((category) => (
          <CategoryRow
            key={category.id}
            category={category}
            busy={busy === category.id}
            onPatch={(change) => patch(category, change)}
          />
        ))}
      </ul>
      {message !== null && <FormMessage text={message} />}
      <TextField
        label="Nouvelle catégorie"
        value={name}
        maxLength={200}
        error={nameError}
        onChange={(event) => {
          setName(event.target.value);
          setNameError(undefined);
        }}
      />
      <Button
        variant="secondary"
        icon={Plus}
        fullWidth
        loading={busy === "new"}
        onClick={() => void add()}
      >
        Ajouter la catégorie
      </Button>
    </section>
  );
}
