import type { AuditAction, JournalMember } from "../../core/gateways/journalContract";
import { ChoiceChips, Disclosure, TextField } from "../../shared/ui";
import { ALL, periodProblem, type JournalFilters } from "./journalFilters";
import { ACTION_LABELS, MODULE_LABELS } from "./journalText";

export interface JournalFiltersPanelProps {
  members: readonly JournalMember[];
  value: JournalFilters;
  onChange: (patch: Partial<JournalFilters>) => void;
}

const ACTIONS: readonly { value: JournalFilters["action"]; label: string }[] = [
  { value: ALL, label: "Toutes" },
  ...Object.entries(ACTION_LABELS).map(([value, label]) => ({
    value: value as AuditAction,
    label,
  })),
];

const MODULES = [
  { value: ALL, label: "Tous" },
  ...Object.entries(MODULE_LABELS).map(([value, label]) => ({ value, label })),
];

/** Période toujours visible ; utilisateur, type et module sous « Filtres » (P4). */
export function JournalFiltersPanel({ members, value, onChange }: JournalFiltersPanelProps) {
  const users = [
    { value: ALL, label: "Tous" },
    ...members.map((member) => ({ value: member.user_id, label: member.name })),
  ];
  return (
    <>
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
          error={periodProblem(value)}
          onChange={(event) => {
            onChange({ to: event.target.value });
          }}
        />
      </div>
      <Disclosure label="Filtres">
        <ChoiceChips
          label="Utilisateur"
          options={users}
          value={value.userId}
          onChange={(userId) => {
            onChange({ userId });
          }}
        />
        <ChoiceChips
          label="Type d'action"
          options={ACTIONS}
          value={value.action}
          onChange={(action) => {
            onChange({ action });
          }}
        />
        <ChoiceChips
          label="Module"
          options={MODULES}
          value={value.module}
          onChange={(module) => {
            onChange({ module });
          }}
        />
      </Disclosure>
    </>
  );
}
