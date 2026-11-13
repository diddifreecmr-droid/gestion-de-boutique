import { useId } from "react";
import { ChevronUp, Trash2 } from "lucide-react";
import type { SaleShortcut } from "../../core/gateways/catalogContract";
import { formatQuantity } from "../../shared/format";
import { Button, QuantityStepper } from "../../shared/ui";
import { articleTitle } from "./articleTitle";
import { meterStock, withQuantity, type LineDraft } from "./draft";
import { stockText } from "./textile";
import { TextileQuantity } from "./TextileQuantity";
import { isBasket, sizeChoices, COMMON_COLORS, UNIT_FIELDS, type LineFields } from "./lineFields";
import { LinePrice } from "./LinePrice";
import { QuickPick } from "./QuickPick";
import type { LineIssues } from "./saleChecks";
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
  /** Quantité déjà prise par les autres lignes du même article (autre taille, autre couleur). */
  reserved?: number;
  /** Replie la carte en une ligne (panier de plusieurs lignes, § 7.4). */
  onCollapse?: () => void;
  /** Raccourcis de longueur du profil (Textile, § 7.5) ; vides ailleurs. */
  shortcuts?: readonly SaleShortcut[];
}

/** Une ligne de la vente : article, stock du lieu, quantité, prix, taille et couleur ou détails. */
export function SaleLineCard(props: SaleLineCardProps) {
  const { line, locationName, issues, showErrors, onChange, onRemove, onCollapse } = props;
  const { fields = UNIT_FIELDS, reserved = 0, shortcuts = [] } = props;
  const titleId = useId();
  const title = articleTitle(line.article.name);
  const basket = isBasket(fields);
  const max = Math.max(line.quantity, line.available - reserved);
  const textile = line.article.sale_mode === "meter";
  // Longueur : une saisie commencée est jugée tout de suite (« 2,55 », stock dépassé).
  const typed = line.mode === "piece" || line.length.trim() !== "";
  const quantityError = showErrors || typed ? issues?.quantity : undefined;
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-4 rounded-lg bg-surface p-4 shadow-card"
    >
      <div className="flex flex-col gap-1">
        <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
          {title}
        </h2>
        <p className="m-0 text-body text-text-muted">
          Stock disponible à {locationName} :{" "}
          {textile
            ? stockText(meterStock(line.article), line.article.piece_length_m)
            : formatQuantity(line.available)}
        </p>
      </div>
      {fields.size && (
        <QuickPick
          label="Taille"
          choices={sizeChoices(line.article.name)}
          value={line.size}
          onChange={(size) => {
            onChange({ ...line, size });
          }}
        />
      )}
      {fields.color && (
        <QuickPick
          label="Couleur"
          choices={COMMON_COLORS}
          value={line.color}
          onChange={(color) => {
            onChange({ ...line, color });
          }}
        />
      )}
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
          max={max}
          onChange={(quantity) => {
            onChange(withQuantity(line, quantity));
          }}
        />
      )}
      <LinePrice
        line={line}
        issues={issues}
        error={showErrors ? issues?.price : undefined}
        basket={basket}
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
      {(onCollapse !== undefined || onRemove !== undefined) && (
        <div className="flex flex-wrap gap-2">
          {onCollapse !== undefined && (
            <Button variant="ghost" icon={ChevronUp} onClick={onCollapse}>
              Replier {title}
            </Button>
          )}
          {onRemove !== undefined && (
            <Button variant="ghost" icon={Trash2} onClick={onRemove}>
              Retirer {title}
            </Button>
          )}
        </div>
      )}
    </section>
  );
}
