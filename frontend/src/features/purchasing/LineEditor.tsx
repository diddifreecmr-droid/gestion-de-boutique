import { Pencil, Trash2 } from "lucide-react";
import { formatMoney } from "../../shared/format";
import { AmountField, Button, ChoiceChips, TextField } from "../../shared/ui";
import { ArticleSearch } from "./ArticleSearch";
import { lineTotal } from "./costing";
import type { DraftArticle, LineDraft, LineProblems } from "./draft";
import type { PurchaseRole } from "./purchasingNav";
import { isTenths, parseEntryQuantity, UNIT_LABELS, unitsFor } from "./units";

export interface LineEditorProps {
  shopId: string;
  role: PurchaseRole;
  index: number;
  line: LineDraft;
  problems: LineProblems | undefined;
  showErrors: boolean;
  onChange: (patch: Partial<LineDraft>) => void;
  /** Absent quand c'est la seule ligne (un achat compte au moins une ligne). */
  onRemove?: (() => void) | undefined;
}

/** Prix de l'unité saisie : « Prix unitaire (par yard) ». */
function priceLabel(line: LineDraft): string {
  if (line.unit === null || line.unit === "UNIT") return "Prix unitaire";
  return `Prix unitaire (par ${UNIT_LABELS[line.unit].toLocaleLowerCase("fr")})`;
}

/** Total de la ligne affiché aussitôt (UC-ACH-01 étape 3), ou `null` tant qu'il manque un chiffre. */
function totalOf(line: LineDraft): number | null {
  if (line.unit === null || line.unitPrice === null) return null;
  const quantity = parseEntryQuantity(line.quantity, line.unit);
  return quantity.ok ? lineTotal(quantity.value, line.unitPrice) : null;
}

/** Une ligne d'achat : article, quantité, unité saisie (RG-X02), prix unitaire, total. */
export function LineEditor(props: LineEditorProps) {
  const { line, problems, showErrors, onChange, index } = props;
  const errors = showErrors ? problems : undefined;
  const select = (article: DraftArticle) => {
    onChange({ article, unit: unitsFor(article)[0] ?? null });
  };
  const units = line.article === null ? [] : unitsFor(line.article);
  const total = totalOf(line);
  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-4 rounded-lg bg-surface p-4 shadow-card">
      <legend className="sr-only">{`Ligne ${String(index + 1)}`}</legend>
      <p aria-hidden="true" className="m-0 text-title-sm font-semibold text-text">
        {`Ligne ${String(index + 1)}`}
      </p>
      {line.article === null ? (
        <ArticleSearch
          shopId={props.shopId}
          role={props.role}
          onSelect={select}
          error={errors?.article}
        />
      ) : (
        <div className="flex flex-col gap-2">
          <span className="text-label font-semibold text-text">Article</span>
          <p className="m-0 break-words text-lead text-text">{line.article.name}</p>
          {errors?.article !== undefined && (
            <p className="m-0 text-body text-danger-text">{errors.article}</p>
          )}
          <Button
            variant="ghost"
            icon={Pencil}
            onClick={() => {
              onChange({ article: null, unit: null });
            }}
          >
            Changer d'article
          </Button>
        </div>
      )}
      {line.article !== null && line.unit !== null && (
        <>
          {units.length > 1 && (
            <ChoiceChips
              label="Unité saisie"
              options={units.map((unit) => ({ value: unit, label: UNIT_LABELS[unit] }))}
              value={line.unit}
              onChange={(unit) => {
                onChange({ unit });
              }}
            />
          )}
          <TextField
            label="Quantité"
            inputMode={isTenths(line.unit) ? "decimal" : "numeric"}
            autoComplete="off"
            hint={line.unit === "YARD" ? "Convertie en mètres (1 yard = 0,9144 m)" : undefined}
            value={line.quantity}
            error={errors?.quantity}
            onChange={(event) => {
              onChange({ quantity: event.target.value });
            }}
          />
          <AmountField
            label={priceLabel(line)}
            value={line.unitPrice}
            error={errors?.price}
            onChange={(unitPrice) => {
              onChange({ unitPrice });
            }}
          />
          <p
            aria-live="polite"
            className="m-0 flex items-baseline justify-between gap-4 text-lead text-text"
          >
            <span>Total de la ligne</span>
            <strong className="tabular-nums">{total === null ? "—" : formatMoney(total)}</strong>
          </p>
        </>
      )}
      {props.onRemove !== undefined && (
        <Button variant="ghost" icon={Trash2} onClick={props.onRemove}>
          {`Retirer la ligne ${String(index + 1)}`}
        </Button>
      )}
    </fieldset>
  );
}
