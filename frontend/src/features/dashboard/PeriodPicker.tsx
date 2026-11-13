import type { PeriodKind } from "../../core/gateways/reportingContract";
import { ChoiceChips, TextField } from "../../shared/ui";
import type { DashboardNav } from "./dashboardNav";
import { PERIOD_LABELS } from "./periods";

/** Périodes du quotidien, toujours visibles (audit UX du 13/11/2026). */
const MAIN = ["today", "yesterday", "month"] as const satisfies readonly PeriodKind[];
/** Les autres, derrière « Autre période ». */
const OTHERS = ["week", "last_month", "custom"] as const satisfies readonly PeriodKind[];
const OTHER = "other";
/** Période retenue à l'appui sur « Autre période » : la première des autres. */
const FIRST_OTHER = OTHERS[0];

type MainValue = (typeof MAIN)[number] | typeof OTHER;

const MAIN_OPTIONS = [
  ...MAIN.map((value) => ({ value, label: PERIOD_LABELS[value] })),
  { value: OTHER, label: "Autre période" },
] as const satisfies readonly { value: MainValue; label: string }[];
const OTHER_OPTIONS = OTHERS.map((value) => ({ value, label: PERIOD_LABELS[value] }));

function isMain(kind: PeriodKind): kind is (typeof MAIN)[number] {
  return (MAIN as readonly PeriodKind[]).includes(kind);
}

function isOther(kind: PeriodKind): kind is (typeof OTHERS)[number] {
  return (OTHERS as readonly PeriodKind[]).includes(kind);
}

/**
 * Sélecteur de période en haut du tableau de bord (UC-TDB-02) : « Aujourd'hui », « Hier »,
 * « Ce mois », et « Autre période » qui ouvre semaine, mois dernier et période libre
 * (« du … au … »). La période reste dans l'adresse : le choix « Autre période » se lit d'elle.
 */
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
  const otherKind = isOther(choice.kind) ? choice.kind : null;
  if (otherKind === null && !isMain(choice.kind)) {
    throw new Error(`Période non rangée dans le sélecteur : « ${choice.kind} »`);
  }
  const mainValue: MainValue = isMain(choice.kind) ? choice.kind : OTHER;
  return (
    <>
      <ChoiceChips
        label="Période"
        options={MAIN_OPTIONS}
        value={mainValue}
        onChange={(value) => {
          if (value === OTHER) {
            if (otherKind === null) nav.choose(FIRST_OTHER, today);
            return;
          }
          nav.choose(value, today);
        }}
      />
      {otherKind !== null && (
        <ChoiceChips
          label="Autre période"
          options={OTHER_OPTIONS}
          value={otherKind}
          onChange={(kind) => {
            nav.choose(kind, today);
          }}
        />
      )}
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
