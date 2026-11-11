import { ChoiceChips, Disclosure } from "../../shared/ui";
import { ALL, type FollowUp, type ListFilters } from "./filters";
import { BAND_CODES, bandLabel, STATUS_CODES, statusOf } from "./labels";
import { sellers, type References } from "./references";

export interface ReceivableFiltersPanelProps {
  refs: References;
  value: ListFilters;
  onChange: (patch: Partial<ListFilters>) => void;
}

const STATUS_OPTIONS = [
  { value: ALL, label: "Tous" },
  ...STATUS_CODES.map((code) => ({ value: code, label: statusOf(code).label })),
] as const;

const BAND_OPTIONS = [
  { value: ALL, label: "Toutes" },
  ...BAND_CODES.map((code) => ({ value: code, label: bandLabel(code) })),
] as const;

const FOLLOW_UP_OPTIONS: readonly { value: FollowUp; label: string }[] = [
  { value: ALL, label: "Toutes" },
  { value: "reminder_overdue", label: "Rappel dépassé" },
  { value: "quiet", label: "Sans versement depuis 30 jours" },
];

/** Statut toujours visible ; vendeur, ancienneté et suivi sous « Filtres » (P4). */
export function ReceivableFiltersPanel({ refs, value, onChange }: ReceivableFiltersPanelProps) {
  const sellerOptions = [
    { value: ALL, label: "Tous les vendeurs" },
    ...sellers(refs).map((member) => ({ value: member.user_id, label: member.name })),
  ];
  return (
    <>
      <ChoiceChips
        label="Statut"
        options={STATUS_OPTIONS}
        value={value.status}
        onChange={(status) => {
          onChange({ status });
        }}
      />
      <Disclosure label="Filtres">
        {refs.me.role === "owner" && (
          <ChoiceChips
            label="Vendeur"
            options={sellerOptions}
            value={value.sellerId}
            onChange={(sellerId) => {
              onChange({ sellerId });
            }}
          />
        )}
        <ChoiceChips
          label="Ancienneté"
          options={BAND_OPTIONS}
          value={value.band}
          onChange={(band) => {
            onChange({ band });
          }}
        />
        <ChoiceChips
          label="Suivi"
          options={FOLLOW_UP_OPTIONS}
          value={value.followUp}
          onChange={(followUp) => {
            onChange({ followUp });
          }}
        />
      </Disclosure>
    </>
  );
}
