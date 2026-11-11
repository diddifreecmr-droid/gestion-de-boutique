import { ChoiceChips, Disclosure, TextField } from "../../shared/ui";
import { ArticleFilter } from "./ArticleFilter";
import { ALL, PERIOD_LABELS, periodProblem, type ListFilters, type Period } from "./listFilters";
import type { References } from "./references";

export interface PurchaseFiltersPanelProps {
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

/** Période toujours visible ; fournisseur, article et lieu sous « Filtres » (P4). */
export function PurchaseFiltersPanel({ shopId, refs, value, onChange }: PurchaseFiltersPanelProps) {
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
        {refs.suppliers.length > 0 && (
          <ChoiceChips
            label="Fournisseur"
            options={withAll(refs.suppliers, "Tous les fournisseurs")}
            value={value.supplierId}
            onChange={(supplierId) => {
              onChange({ supplierId });
            }}
          />
        )}
        <ArticleFilter
          shopId={shopId}
          value={value.article}
          onChange={(article) => {
            onChange({ article });
          }}
        />
        <ChoiceChips
          label="Lieu de réception"
          options={withAll(refs.locations, "Tous les lieux")}
          value={value.locationId}
          onChange={(locationId) => {
            onChange({ locationId });
          }}
        />
      </Disclosure>
    </>
  );
}
