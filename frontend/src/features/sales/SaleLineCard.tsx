import { useId } from "react";
import { Trash2 } from "lucide-react";
import type { SaleShortcut } from "../../core/gateways/catalogContract";
import { formatQuantity } from "../../shared/format";
import { Button, QuantityStepper } from "../../shared/ui";
import { articleTitle } from "./articleTitle";
import { meterStock, unitStock, withQuantity, type LineDraft } from "./draft";
import { UNIT_FIELDS, type LineFields } from "./lineFields";
import { LinePrice } from "./LinePrice";
import type { LineIssues } from "./saleChecks";
import { statusOf, usePieceWords } from "./saleStock";
import { StockStatusBadge } from "./StockStatusBadge";
import { stockText } from "./textile";
import { TextileQuantity } from "./TextileQuantity";
import { UnitDetailsFields } from "./UnitDetailsFields";

export interface SaleLineCardProps {
  line: LineDraft;
  locationName: string;
  issues: LineIssues | undefined;
  /** Montrer les erreurs (après un premier appui sur « Valider »). */
  showErrors: boolean;
  onChange: (line: LineDraft) => void;
  /** Absent pour la seule ligne de la vente. */
  onRemove?: () => void;
  /** Champs de la ligne selon le profil (Motos par défaut : détails par unité). */
  fields?: LineFields;
  /** Raccourcis de longueur du profil (Textile, § 7.5) ; vides ailleurs. */
  shortcuts?: readonly SaleShortcut[];
}

/** Stock de la ligne : chiffre du lieu (gérant, Motos) ou pastille seule (employé, 2026-11-15). */
function LineStock({ line, locationName }: { line: LineDraft; locationName: string }) {
  const words = usePieceWords();
  const { article } = line;
  if (article.available === null) {
    return (
      <p className="m-0 flex items-center gap-2 text-body text-text-muted">
        Stock : <StockStatusBadge status={statusOf(article, true)} />
      </p>
    );
  }
  const text =
    article.sale_mode === "meter"
      ? stockText(meterStock(article), article.piece_length_m, words)
      : formatQuantity(String(unitStock(article)));
  return (
    <p className="m-0 text-body text-text-muted">
      Stock disponible à {locationName} : {text}
    </p>
  );
}

/** Une ligne de la vente : article, stock du lieu, quantité, prix (et détails par unité, Motos). */
export function SaleLineCard(props: SaleLineCardProps) {
  const { line, locationName, issues, showErrors, onChange, onRemove } = props;
  const { fields = UNIT_FIELDS, shortcuts = [] } = props;
  const titleId = useId();
  const title = articleTitle(line.article.name);
  const textile = line.article.sale_mode === "meter";
  // Longueur : une saisie commencée est jugée tout de suite (« 2,55 », stock dépassé).
  const typed = line.mode === "piece" || line.length.trim() !== "";
  const quantityError = showErrors || typed ? issues?.quantity : undefined;
  const max = line.available === null ? {} : { max: Math.max(line.quantity, line.available) };
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-4 rounded-lg bg-surface p-4 shadow-card"
    >
      <div className="flex flex-col gap-1">
        <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
          {title}
        </h2>
        <LineStock line={line} locationName={locationName} />
      </div>
      {textile ? (
        <TextileQuantity
          line={line}
          shortcuts={shortcuts}
          error={quantityError}
          onChange={onChange}
        />
      ) : (
        <QuantityStepper
          inline
          label="Quantité"
          value={line.quantity}
          {...max}
          onChange={(quantity) => {
            onChange(withQuantity(line, quantity));
          }}
        />
      )}
      <LinePrice
        line={line}
        issues={issues}
        error={showErrors ? issues?.price : undefined}
        basket={!fields.units}
        onChange={(unitPrice) => {
          onChange({ ...line, unitPrice });
        }}
      />
      {fields.units && (
        <UnitDetailsFields
          line={line}
          chassisErrors={showErrors ? (issues?.chassis ?? []) : []}
          onChange={onChange}
        />
      )}
      {onRemove !== undefined && (
        <Button variant="ghost" icon={Trash2} onClick={onRemove}>
          Retirer {title}
        </Button>
      )}
    </section>
  );
}
