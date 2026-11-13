import { useId } from "react";
import { AlertTriangle, Trash2 } from "lucide-react";
import { useActiveProfile } from "../../core/profile/activeProfile";
import { formatMoney, formatQuantity } from "../../shared/format";
import { AmountField, Button, Disclosure, QuantityStepper, TextField } from "../../shared/ui";
import { articleTitle } from "./articleTitle";
import { withQuantity, type LineDraft, type UnitDetail } from "./draft";
import type { LineIssues } from "./saleChecks";

export interface SaleLineCardProps {
  line: LineDraft;
  locationName: string;
  issues: LineIssues | undefined;
  /** Montrer les erreurs (après un premier appui sur « Valider »). */
  showErrors: boolean;
  onChange: (line: LineDraft) => void;
  /** Absent pour la seule ligne de la vente. */
  onRemove?: () => void;
}

/** Une ligne de la vente : article, stock du lieu, quantité, prix, détails par unité. */
export function SaleLineCard({
  line,
  locationName,
  issues,
  showErrors,
  onChange,
  onRemove,
}: SaleLineCardProps) {
  const titleId = useId();
  const unit = line.article.unit_label;
  const priceError = showErrors ? issues?.price : undefined;
  const title = articleTitle(line.article.name);
  const asked = askedFields(useActiveProfile().saleFields);
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
          Stock disponible à {locationName} : {formatQuantity(line.available)}
        </p>
      </div>
      <QuantityStepper
        inline
        label="Quantité"
        value={line.quantity}
        max={line.available}
        onChange={(quantity) => {
          onChange(withQuantity(line, quantity));
        }}
      />
      <AmountField
        label={line.quantity > 1 ? `Prix d'une ${unit}` : "Prix"}
        value={line.unitPrice}
        error={priceError}
        onChange={(unitPrice) => {
          onChange({ ...line, unitPrice });
        }}
      />
      {issues?.belowMinimum !== undefined && (
        <p className="m-0 flex items-start gap-2 text-body text-warning-text">
          <AlertTriangle aria-hidden="true" className="size-6 shrink-0" />
          <span>
            {issues.approvalRequired === true
              ? `Prix inférieur au minimum (${formatMoney(issues.belowMinimum)}) : validation du propriétaire nécessaire.`
              : `Prix inférieur au minimum de ${formatMoney(issues.belowMinimum)}`}
          </span>
        </p>
      )}
      {asked.size > 0 && (
        <Disclosure label="Détails de l'article">
          {line.units.map((detail, index) => (
            <UnitFields
              key={index}
              title={`${unit} ${String(index + 1)}`}
              asked={asked}
              detail={detail}
              chassisError={showErrors ? issues?.chassis[index] : undefined}
              onChange={(next) => {
                onChange({ ...line, units: line.units.map((u, i) => (i === index ? next : u)) });
              }}
            />
          ))}
        </Disclosure>
      )}
      {onRemove !== undefined && (
        <Button variant="ghost" icon={Trash2} onClick={onRemove}>
          Retirer {title}
        </Button>
      )}
    </section>
  );
}

/** Détails par unité que l'écran sait saisir, par code de champ de vente du profil. */
const UNIT_FIELDS = ["color", "chassis_number", "engine_number"] as const;
type UnitField = (typeof UNIT_FIELDS)[number];

/** Les détails par unité **demandés par le profil** (couleur, châssis, moteur : Motos). */
function askedFields(saleFields: readonly { code: string }[]): ReadonlySet<UnitField> {
  const codes = new Set(saleFields.map((field) => field.code));
  return new Set(UNIT_FIELDS.filter((code) => codes.has(code)));
}

function UnitFields({
  title,
  asked,
  detail,
  chassisError,
  onChange,
}: {
  title: string;
  asked: ReadonlySet<UnitField>;
  detail: UnitDetail;
  chassisError: string | undefined;
  onChange: (detail: UnitDetail) => void;
}) {
  return (
    <fieldset className="m-0 flex flex-col gap-4 border-0 p-0">
      <legend className="mb-2 p-0 text-label font-semibold text-text-muted">{title}</legend>
      {asked.has("color") && (
        <TextField
          label={`Couleur — ${title}`}
          value={detail.color}
          onChange={(event) => {
            onChange({ ...detail, color: event.target.value });
          }}
        />
      )}
      {asked.has("chassis_number") && (
        <TextField
          label={`N° de châssis — ${title}`}
          value={detail.chassis}
          error={chassisError}
          autoCapitalize="characters"
          onChange={(event) => {
            onChange({ ...detail, chassis: event.target.value });
          }}
        />
      )}
      {asked.has("engine_number") && (
        <TextField
          label={`N° de moteur — ${title}`}
          value={detail.engine}
          autoCapitalize="characters"
          onChange={(event) => {
            onChange({ ...detail, engine: event.target.value });
          }}
        />
      )}
    </fieldset>
  );
}
