import { useState } from "react";
import { Ban, Check, Pencil, RotateCcw } from "lucide-react";
import type { ExpenseCategory, ExpenseCategoryPatch } from "../../core/gateways/expensesContract";
import { Badge, Button, TextField } from "../../shared/ui";

/** Refus explicite (UC-DEP-02) : les 5 catégories de départ se renomment seulement. */
export const BASE_LOCKED = "Catégorie de base : elle se renomme mais ne se désactive pas";

export interface CategoryRowProps {
  category: ExpenseCategory;
  busy: boolean;
  onPatch: (patch: Omit<ExpenseCategoryPatch, "version">) => Promise<boolean>;
}

/** Une catégorie dans les réglages : renommer, désactiver ou réactiver. */
export function CategoryRow({ category, busy, onPatch }: CategoryRowProps) {
  const [name, setName] = useState<string | null>(null);
  const [error, setError] = useState<string | undefined>(undefined);

  const rename = async () => {
    if (name === null) return;
    if (name.trim() === "") {
      setError("Le nom est vide");
      return;
    }
    if (await onPatch({ name: name.trim() })) setName(null);
  };

  return (
    <li className="flex flex-col gap-2 px-4 py-3">
      <span className="flex flex-wrap items-center gap-2">
        <span className={`text-lead ${category.active ? "text-text" : "text-text-muted"}`}>
          {category.name}
        </span>
        {category.is_base && <Badge status="success">De base</Badge>}
        {!category.active && <Badge status="danger">Désactivée</Badge>}
      </span>
      {name !== null ? (
        <div className="flex flex-col gap-2">
          <TextField
            label={`Nouveau nom pour ${category.name}`}
            value={name}
            maxLength={200}
            error={error}
            onChange={(event) => {
              setName(event.target.value);
              setError(undefined);
            }}
          />
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="secondary"
              fullWidth
              onClick={() => {
                setName(null);
              }}
            >
              Retour
            </Button>
            <Button
              variant="secondary"
              icon={Check}
              fullWidth
              loading={busy}
              onClick={() => void rename()}
            >
              Enregistrer
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            icon={Pencil}
            onClick={() => {
              setName(category.name);
            }}
          >
            Renommer
          </Button>
          {category.active ? (
            <Button
              variant="secondary"
              icon={Ban}
              loading={busy}
              onClick={() => void onPatch({ active: false })}
              {...(category.is_base ? { disabledReason: BASE_LOCKED } : {})}
            >
              Désactiver
            </Button>
          ) : (
            <Button
              variant="secondary"
              icon={RotateCcw}
              loading={busy}
              onClick={() => void onPatch({ active: true })}
            >
              Réactiver
            </Button>
          )}
        </div>
      )}
    </li>
  );
}
