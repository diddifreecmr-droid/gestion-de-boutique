import { useId } from "react";
import { Check } from "lucide-react";
import type { SaleReturns, StockCondition } from "../../../core/gateways/returnsContract";
import type { SaleResult } from "../../../core/gateways/salesContract";
import { formatMoney, formatQuantity } from "../../../shared/format";
import { Button, ChoiceChips, QuantityStepper } from "../../../shared/ui";
import { chassisLeft, needsChassis, type LinePick } from "./returnDraft";
import { returnableOf } from "./returnMath";

const CONDITIONS = [
  { value: "sellable", label: "Vendable" },
  { value: "damaged", label: "Abîmé" },
] as const satisfies readonly { value: StockCondition; label: string }[];

export interface ReturnLinesSectionProps {
  sale: SaleResult;
  listing: SaleReturns;
  picks: Record<number, LinePick>;
  errors: Record<number, string>;
  linesError: string | undefined;
  onChange: (line: number, pick: LinePick) => void;
}

const EMPTY: LinePick = { quantity: 0, condition: "sellable", chassis: [] };

/**
 * Articles rendus (UC-VEN-09) : quantité bornée par « encore rendable », état au retour en
 * stock (Vendable / Abîmé), châssis rendus quand la ligne n'est rendue qu'en partie.
 */
export function ReturnLinesSection(props: ReturnLinesSectionProps) {
  const { sale, listing, picks, errors, linesError, onChange } = props;
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-4 rounded-lg bg-surface p-4 shadow-card"
    >
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Articles rendus
      </h2>
      {linesError !== undefined && <p className="m-0 text-body text-danger-text">{linesError}</p>}
      {sale.lines.map((sold, index) => {
        const line = index + 1;
        const returnable = returnableOf(listing, line);
        const pick = picks[line] ?? EMPTY;
        const name = sold.article_name;
        return (
          <div
            key={line}
            className="flex flex-col gap-4 border-t border-border pt-4 first:border-0"
          >
            <p className="m-0 flex items-baseline justify-between gap-4 text-lead text-text">
              <span className="break-words">{name}</span>
              <span className="shrink-0 tabular-nums">
                {formatQuantity(sold.quantity)} × {formatMoney(sold.unit_price)}
              </span>
            </p>
            {returnable <= 0 ? (
              <p className="m-0 text-body text-text-muted">Déjà rendu en entier.</p>
            ) : !Number.isInteger(returnable) ? (
              <p className="m-0 text-body text-text-muted">
                Retour d'une quantité au mètre : à venir sur cet écran.
              </p>
            ) : (
              <>
                <QuantityStepper
                  label={`Quantité rendue — ${name}`}
                  value={pick.quantity}
                  min={0}
                  max={returnable}
                  hint={`Encore rendable : ${formatQuantity(returnable)}`}
                  onChange={(quantity) => {
                    onChange(line, { ...pick, quantity, chassis: pick.chassis.slice(0, quantity) });
                  }}
                />
                {pick.quantity > 0 && (
                  <ChoiceChips
                    label={`État au retour — ${name}`}
                    options={CONDITIONS}
                    value={pick.condition}
                    onChange={(condition) => {
                      onChange(line, { ...pick, condition });
                    }}
                  />
                )}
                {needsChassis(sale, listing, line, pick) && (
                  <ChassisChoice
                    label={`Châssis rendus — ${name}`}
                    options={chassisLeft(sale, listing, line)}
                    chosen={pick.chassis}
                    error={errors[line]}
                    onChange={(chassis) => {
                      onChange(line, { ...pick, chassis });
                    }}
                  />
                )}
              </>
            )}
          </div>
        );
      })}
    </section>
  );
}

function ChassisChoice(props: {
  label: string;
  options: string[];
  chosen: string[];
  error: string | undefined;
  onChange: (chassis: string[]) => void;
}) {
  const { label, options, chosen, error, onChange } = props;
  const labelId = useId();
  return (
    <div role="group" aria-labelledby={labelId} className="flex flex-col gap-2">
      <p id={labelId} className="m-0 text-label font-semibold text-text">
        {label}
      </p>
      <div className="grid grid-cols-2 gap-2">
        {options.map((chassis) => {
          const on = chosen.includes(chassis);
          return (
            <Button
              key={chassis}
              variant="secondary"
              aria-pressed={on}
              {...(on ? { icon: Check } : {})}
              onClick={() => {
                onChange(on ? chosen.filter((c) => c !== chassis) : [...chosen, chassis]);
              }}
            >
              <span className="font-mono">{chassis}</span>
            </Button>
          );
        })}
      </div>
      {error !== undefined && <p className="m-0 text-body text-danger-text">{error}</p>}
    </div>
  );
}
