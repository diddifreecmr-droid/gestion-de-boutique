import { useModules } from "../../core/profile/modulesContext";
import { ChoiceChips, SearchField, TextField } from "../../shared/ui";
import { PeriodBar } from "../expenses/PeriodBar";
import { saleSearchLabel } from "./profileLabels";
import { activeSaleFilters, ALL, periodProblem, type ListFilters } from "./saleFilters";
import type { SaleRefs } from "./saleRefs";

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
 * Recherche (n° de vente, ou de châssis pour un profil qui en saisit ; toutes dates), puis
 * période et « Filtres » sur une ligne (`PeriodBar`, audit UX du 13/11/2026) : mode,
 * comptant/crédit et vendeur (propriétaire seulement) sous « Filtres » (P4).
 */
export function SaleFiltersPanel({ refs, value, onChange }: SaleFiltersPanelProps) {
  const credit = useModules().has("receivables");
  const problem = periodProblem(value);
  const searching = value.text.trim() !== "";
  const sellers = refs.members.filter((m) => m.role === "seller" || m.role === "owner");
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
    <>
      <SearchField
        label={saleSearchLabel(refs.searchChassis)}
        value={value.text}
        onChange={(text) => {
          onChange({ text });
        }}
      />
      <PeriodBar
        value={value.period}
        onChange={(period) => {
          onChange({ period });
        }}
        dates={dates}
        problem={problem}
        showPeriod={!searching}
        activeFilters={activeSaleFilters(value)}
      >
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
      </PeriodBar>
    </>
  );
}
