import { useModules } from "../../core/profile/modulesContext";
import { ChoiceChips, Disclosure, SearchField, TextField } from "../../shared/ui";
import { ALL, PERIOD_LABELS, periodProblem, type ListFilters, type Period } from "./saleFilters";
import type { SaleRefs } from "./saleRefs";

const PERIODS = Object.entries(PERIOD_LABELS).map(([value, label]) => ({
  value: value as Period,
  label,
}));

const KINDS = [
  { value: ALL, label: "Toutes" },
  { value: "cash", label: "Comptant" },
  { value: "credit", label: "Crédit" },
] as const;

function withAll(items: readonly { id: string; name: string }[], all: string) {
  return [
    { value: ALL, label: all },
    ...items.map((item) => ({ value: item.id, label: item.name })),
  ];
}

export interface SaleFiltersPanelProps {
  refs: SaleRefs;
  value: ListFilters;
  onChange: (patch: Partial<ListFilters>) => void;
}

/**
 * Recherche (n° ou châssis, toutes dates) et période toujours visibles ; mode, comptant/crédit
 * et vendeur (propriétaire seulement) sous « Filtres » (P4).
 */
export function SaleFiltersPanel({ refs, value, onChange }: SaleFiltersPanelProps) {
  const credit = useModules().has("receivables");
  const problem = periodProblem(value);
  const searching = value.text.trim() !== "";
  const sellers = refs.members.filter((m) => m.role === "seller" || m.role === "owner");
  return (
    <>
      <SearchField
        label="Chercher une vente"
        hint="N° de vente ou de châssis, toutes dates"
        value={value.text}
        onChange={(text) => {
          onChange({ text });
        }}
      />
      {!searching && (
        <ChoiceChips
          label="Période"
          options={PERIODS}
          value={value.period}
          onChange={(period) => {
            onChange({ period });
          }}
        />
      )}
      {!searching && value.period === "custom" && (
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
        {credit && (
          <ChoiceChips
            label="Comptant ou crédit"
            options={KINDS}
            value={value.kind}
            onChange={(kind) => {
              onChange({ kind });
            }}
          />
        )}
        <ChoiceChips
          label="Mode de paiement"
          options={withAll(refs.modes, "Tous les modes")}
          value={value.modeId}
          onChange={(modeId) => {
            onChange({ modeId });
          }}
        />
        {refs.role === "owner" && (
          <ChoiceChips
            label="Vendeur"
            options={withAll(
              sellers.map((m) => ({ id: m.user_id, name: m.name })),
              "Tous les vendeurs",
            )}
            value={value.sellerId}
            onChange={(sellerId) => {
              onChange({ sellerId });
            }}
          />
        )}
      </Disclosure>
    </>
  );
}
