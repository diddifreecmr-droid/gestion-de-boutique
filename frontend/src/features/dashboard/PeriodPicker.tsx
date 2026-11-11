import type { PeriodKind } from "../../core/gateways/reportingContract";
import { ChoiceChips, TextField } from "../../shared/ui";
import { PERIOD_KINDS, type DashboardNav } from "./dashboardNav";
import { PERIOD_LABELS } from "./periods";

const OPTIONS = PERIOD_KINDS.map((value: PeriodKind) => ({ value, label: PERIOD_LABELS[value] }));

/** Sélecteur de période en haut de l'accueil (UC-TDB-02) ; « du … au … » pour la période libre. */
export function PeriodPicker({
  nav,
  today,
  problem,
}: {
  nav: DashboardNav;
  today: string;
  problem: string | undefined;
}) {
  const { choice } = nav;
  return (
    <>
      <ChoiceChips
        label="Période"
        options={OPTIONS}
        value={choice.kind}
        onChange={(kind) => {
          nav.choose(kind, today);
        }}
      />
      {choice.kind === "custom" && (
        <div className="grid grid-cols-2 gap-4">
          <TextField
            label="Du"
            type="date"
            max={today}
            value={choice.from}
            onChange={(event) => {
              nav.range(event.target.value, choice.to);
            }}
          />
          <TextField
            label="Au"
            type="date"
            max={today}
            value={choice.to}
            error={problem}
            onChange={(event) => {
              nav.range(choice.from, event.target.value);
            }}
          />
        </div>
      )}
    </>
  );
}
