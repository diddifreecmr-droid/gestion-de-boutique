import { Disclosure, TextField } from "../../shared/ui";
import type { LineDraft, UnitDetail } from "./draft";

export interface UnitDetailsFieldsProps {
  line: LineDraft;
  onChange: (line: LineDraft) => void;
}

/**
 * « Détails de l'article » : la couleur de chaque unité (Motos). Les n° de châssis et de moteur
 * ne sont plus saisis (décision client du 2026-11-15 : sans intérêt pour la boutique) ; le
 * serveur les accepte toujours, facultatifs.
 */
export function UnitDetailsFields({ line, onChange }: UnitDetailsFieldsProps) {
  const unit = line.article.unit_label;
  return (
    <Disclosure label="Détails de l'article">
      {line.units.map((detail, index) => (
        <UnitFields
          key={index}
          title={`${unit} ${String(index + 1)}`}
          detail={detail}
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
  onChange,
}: {
  title: string;
  detail: UnitDetail;
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
    </fieldset>
  );
}
