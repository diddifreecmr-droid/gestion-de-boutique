import { useId, useState, type ReactNode } from "react";
import { ChevronDown, SlidersHorizontal } from "lucide-react";
import { Button, ChoiceChips } from "../../shared/ui";
import { PERIOD_LABELS, type Period } from "./filters";

const PERIODS = Object.entries(PERIOD_LABELS).map(([value, label]) => ({
  value: value as Period,
  label,
}));

export interface PeriodBarProps {
  value: Period;
  onChange: (period: Period) => void;
  /** Champs « Du » / « Au », montrés sous le choix quand la période est « Autres dates ». */
  dates: ReactNode;
  /** Période incomplète ou à l'envers : le choix reste ouvert pour la corriger. */
  problem: string | undefined;
  /** Faux pendant une recherche (toutes dates) : seul « Filtres » reste. */
  showPeriod?: boolean;
  /** Nombre de filtres actifs, lu dans le bouton (« Filtres (2) »). */
  activeFilters: number;
  /** Filtres secondaires, sous « Filtres » (P4). */
  children: ReactNode;
}

type Panel = "period" | "filters" | null;

/**
 * Période et filtres sur **une** ligne (audit UX du 13/11/2026) : « Aujourd'hui ▾ » ouvre le
 * choix de la période (refermé dès qu'un choix est fait, sauf « Autres dates ») ; « Filtres »
 * ouvre les autres filtres. Un seul panneau ouvert à la fois, dans le flux de la page.
 */
export function PeriodBar(props: PeriodBarProps) {
  const { value, onChange, dates, problem, showPeriod = true, activeFilters, children } = props;
  if (!Number.isSafeInteger(activeFilters) || activeFilters < 0) {
    throw new Error(`PeriodBar : nombre de filtres invalide (${String(activeFilters)})`);
  }
  const [open, setOpen] = useState<Panel>(null);
  const periodId = useId();
  const filtersId = useId();
  const toggle = (panel: Exclude<Panel, null>) => {
    setOpen((current) => (current === panel ? null : panel));
  };
  const periodOpen = showPeriod && (open === "period" || problem !== undefined);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2">
        {showPeriod && (
          <div className="min-w-0 flex-1">
            <Button
              variant="secondary"
              fullWidth
              aria-label={`Période : ${PERIOD_LABELS[value]}`}
              aria-expanded={periodOpen}
              aria-controls={periodId}
              onClick={() => {
                toggle("period");
              }}
            >
              <span className="inline-flex items-center gap-1">
                {PERIOD_LABELS[value]}
                <ChevronDown aria-hidden="true" className="size-6 shrink-0" />
              </span>
            </Button>
          </div>
        )}
        <div className={showPeriod ? "shrink-0" : "flex-1"}>
          <Button
            variant="secondary"
            icon={SlidersHorizontal}
            fullWidth
            aria-expanded={open === "filters"}
            aria-controls={filtersId}
            onClick={() => {
              toggle("filters");
            }}
          >
            {activeFilters === 0 ? "Filtres" : `Filtres (${String(activeFilters)})`}
          </Button>
        </div>
      </div>
      {showPeriod && (
        <div id={periodId} hidden={!periodOpen} className="flex flex-col gap-4">
          <ChoiceChips
            label="Période"
            options={PERIODS}
            value={value}
            onChange={(period) => {
              onChange(period);
              setOpen(period === "custom" ? "period" : null);
            }}
          />
          {value === "custom" && dates}
        </div>
      )}
      <div id={filtersId} hidden={open !== "filters"} className="flex flex-col gap-4">
        {children}
      </div>
    </div>
  );
}
