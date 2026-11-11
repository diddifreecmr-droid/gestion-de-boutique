import { ChoiceChips, Disclosure, TextField } from "../../shared/ui";
import { ALL, PERIOD_LABELS, periodProblem, type ListFilters, type Period } from "./filters";
import type { References } from "./references";
import { TagFilter } from "./TagFilter";

export interface ExpenseFiltersPanelProps {
  shopId: string;
  refs: References;
  value: ListFilters;
  onChange: (patch: Partial<ListFilters>) => void;
}

const PERIODS = Object.entries(PERIOD_LABELS).map(([value, label]) => ({
  value: value as Period,
  label,
}));

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

/** Période toujours visible ; les autres filtres sous « Filtres » (P4, le minimum visible). */
export function ExpenseFiltersPanel({ shopId, refs, value, onChange }: ExpenseFiltersPanelProps) {
  const problem = periodProblem(value);
  return (
    <>
      <ChoiceChips
        label="Période"
        options={PERIODS}
        value={value.period}
        onChange={(period) => {
          onChange({ period });
        }}
      />
      {value.period === "custom" && (
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
      )}
      <Disclosure label="Filtres">
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
      </Disclosure>
    </>
  );
}
