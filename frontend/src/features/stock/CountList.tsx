import { useState } from "react";
import type { Inventory } from "../../core/gateways/stockContract";
import { EmptyState, SearchField, TextField } from "../../shared/ui";
import type { Drafts } from "./inventoryDrafts";
import { quantityHint } from "./quantities";

export interface CountListProps {
  inventory: Inventory;
  drafts: Drafts;
  errors: Readonly<Record<string, string>>;
  onChange: (articleId: string, text: string) => void;
}

/**
 * Une case « Quantité comptée » par article du lieu (UC-STK-07, étape 1). Seule la quantité
 * comptée est affichée : la quantité théorique n'existe pas dans la ligne d'un inventaire en
 * cours (INV-01), elle ne peut pas influencer le comptage.
 */
export function CountList({ inventory, drafts, errors, onChange }: CountListProps) {
  const [text, setText] = useState("");
  const typed = text.trim().toLocaleLowerCase("fr");
  const lines = inventory.lines.filter((line) =>
    line.display_name.toLocaleLowerCase("fr").includes(typed),
  );
  return (
    <>
      {inventory.lines.length > 5 && (
        <SearchField label="Trouver un article" value={text} onChange={setText} />
      )}
      {lines.length === 0 && (
        <EmptyState
          message={
            inventory.lines.length === 0
              ? "Aucun article actif à compter."
              : `Aucun article ne correspond à « ${text.trim()} ».`
          }
        />
      )}
      <ul aria-label="Quantités comptées" className="m-0 flex list-none flex-col gap-4 p-0">
        {lines.map((line) => (
          <li key={line.article_id} className="rounded-lg bg-surface p-4 shadow-card">
            <TextField
              label={line.display_name}
              hint={quantityHint(line.stock_unit) ?? "Quantité comptée"}
              inputMode="decimal"
              autoComplete="off"
              value={drafts[line.article_id] ?? ""}
              error={errors[line.article_id]}
              onChange={(event) => {
                onChange(line.article_id, event.target.value);
              }}
            />
          </li>
        ))}
      </ul>
    </>
  );
}
