import { ArrowLeft } from "lucide-react";
import { Button } from "../../shared/ui";
import { CategorySettings } from "./CategorySettings";
import type { ScreenProps } from "./expenseNav";
import { TagMerge } from "./TagMerge";

/** Réglages des dépenses (UC-DEP-02) : propriétaire seulement (garde dans `ExpensesPage`). */
export function ExpenseSettings({
  shopId,
  refs,
  nav,
  onChanged,
}: ScreenProps & { onChanged: () => void }) {
  if (refs.me.role !== "owner") {
    throw new Error("Réglages des dépenses réservés au propriétaire (garde manquante)");
  }
  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
        Retour aux dépenses
      </Button>
      <h1 className="m-0 text-title font-bold text-text">Catégories et tags</h1>
      <CategorySettings shopId={shopId} onChanged={onChanged} />
      <TagMerge shopId={shopId} />
    </>
  );
}
