import { Disclosure, TextField } from "../../shared/ui";
import type { LineDraft, UnitDetail } from "./draft";

export interface UnitDetailsFieldsProps {
  line: LineDraft;
  /** Erreur de châssis par unité (déjà filtrée par « montrer les erreurs »). */
  chassisErrors: readonly (string | undefined)[];
  onChange: (line: LineDraft) => void;
}

/** « Détails de l'article » : une fiche par unité (couleur, châssis, moteur — CDC § 17.3). */
export function UnitDetailsFields({ line, chassisErrors, onChange }: UnitDetailsFieldsProps) {
  const unit = line.article.unit_label;
  return (
    <Disclosure label="Détails de l'article">
      {line.units.map((detail, index) => (
        <UnitFields
          key={index}
          title={`${unit} ${String(index + 1)}`}
          detail={detail}
          chassisError={chassisErrors[index]}
          onChange={(next) => {
            onChange({ ...line, units: line.units.map((u, i) => (i === index ? next : u)) });
          }}
        />
      ))}
    </Disclosure>
  );
}

function UnitFields({
  title,
  detail,
  chassisError,
  onChange,
}: {
  title: string;
  detail: UnitDetail;
  chassisError: string | undefined;
  onChange: (detail: UnitDetail) => void;
}) {
  return (
    <fieldset className="m-0 flex flex-col gap-4 border-0 p-0">
      <legend className="mb-2 p-0 text-label font-semibold text-text-muted">{title}</legend>
      <TextField
        label={`Couleur — ${title}`}
        value={detail.color}
        onChange={(event) => {
          onChange({ ...detail, color: event.target.value });
        }}
      />
      <TextField
        label={`N° de châssis — ${title}`}
        value={detail.chassis}
        error={chassisError}
        autoCapitalize="characters"
        onChange={(event) => {
          onChange({ ...detail, chassis: event.target.value });
        }}
      />
      <TextField
        label={`N° de moteur — ${title}`}
        value={detail.engine}
        autoCapitalize="characters"
        onChange={(event) => {
          onChange({ ...detail, engine: event.target.value });
        }}
      />
    </fieldset>
  );
}
