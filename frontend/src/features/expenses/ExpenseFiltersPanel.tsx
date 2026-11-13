import { ChoiceChips, TextField } from "../../shared/ui";
import { activeExpenseFilters, ALL, periodProblem, type ListFilters } from "./filters";
import { PeriodBar } from "./PeriodBar";
import type { References } from "./references";
import { TagFilter } from "./TagFilter";

export interface ExpenseFiltersPanelProps {
  shopId: string;
  refs: References;
  value: ListFilters;
  onChange: (patch: Partial<ListFilters>) => void;
}

/** Choix exclusif précédé de « Tous » (aucun filtre). */
function withAll(items: readonly { id: string; name: string }[], all: string) {
  return [
    { value: ALL, label: all },
    ...items.map((item) => ({ value: item.id, label: item.name })),
  ];
}

/** Auteurs proposés : les membres pour le propriétaire ; « Moi » pour le comptable. */
function authors(refs: References) {
  if (refs.me.role !== "owner") return [{ id: refs.me.userId, name: "Moi" }];
  return [...refs.members].map(([id, name]) => ({ id, name }));
}

/** Période et « Filtres » sur une ligne (`PeriodBar`) ; les autres filtres dessous (P4). */
export function ExpenseFiltersPanel({ shopId, refs, value, onChange }: ExpenseFiltersPanelProps) {
  const problem = periodProblem(value);
  const dates = (
    <div className="grid grid-cols-2 gap-4">
      <TextField
        label="Du"
        type="date"
        value={value.from}
        onChange={(event) => {
          onChange({ from: event.target.value });
        }}
      />
      <TextField
        label="Au"
        type="date"
        value={value.to}
        error={problem}
        onChange={(event) => {
          onChange({ to: event.target.value });
        }}
      />
    </div>
  );
  return (
    <PeriodBar
      value={value.period}
      onChange={(period) => {
        onChange({ period });
      }}
      dates={dates}
      problem={problem}
      activeFilters={activeExpenseFilters(value)}
    >
      <ChoiceChips
        label="Catégorie"
        options={withAll(refs.categories, "Toutes")}
        value={value.categoryId}
        onChange={(categoryId) => {
          onChange({ categoryId });
        }}
      />
      <TagFilter
        shopId={shopId}
        value={value.tag}
        onChange={(tag) => {
          onChange({ tag });
        }}
      />
      {refs.locations.length > 0 && (
        <ChoiceChips
          label="Lieu"
          options={withAll(refs.locations, "Tous les lieux")}
          value={value.locationId}
          onChange={(locationId) => {
            onChange({ locationId });
          }}
        />
      )}
      <ChoiceChips
        label="Auteur"
        options={withAll(authors(refs), "Tous les auteurs")}
        value={value.userId}
        onChange={(userId) => {
          onChange({ userId });
        }}
      />
      <ChoiceChips
        label="Mode de paiement"
        options={withAll(refs.modes, "Tous les modes")}
        value={value.modeId}
        onChange={(modeId) => {
          onChange({ modeId });
        }}
      />
    </PeriodBar>
  );
}
