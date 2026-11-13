import type { ReactNode } from "react";
import type { ProfileFieldResponse } from "../../core/gateways/catalogAdminContract";
import { Disclosure } from "../../shared/ui";
import type { FieldDraft, FieldErrors } from "./fieldValues";
import { ProfileFieldInput } from "./ProfileFieldInput";
import { shownFields, TEXTILE_MAIN } from "./textileFields";

export interface ArticleFieldsEditorProps {
  fields: readonly ProfileFieldResponse[];
  draft: FieldDraft;
  errors: FieldErrors;
  onChange: (code: string, value: string) => void;
  /** Champs visibles après les obligatoires (ex. prix de base du propriétaire). */
  main?: ReactNode;
  /** Champs facultatifs hors profil (seuil d'alerte, notes), sous « Plus de détails ». */
  extra: ReactNode;
}

/**
 * Champs d'article du profil (CDC § 17.2) : obligatoires visibles, facultatifs repliés sous
 * « Plus de détails » (P4) — ouvert d'emblée si l'un d'eux est rempli ou en erreur. Textile :
 * unité, vente à la pièce et longueur restent visibles, chacun seulement quand il a un sens.
 */
export function ArticleFieldsEditor(props: ArticleFieldsEditorProps) {
  const { draft, errors, onChange, main, extra } = props;
  const fields = shownFields(props.fields, draft);
  const input = (spec: ProfileFieldResponse) => (
    <ProfileFieldInput
      key={spec.code}
      spec={spec}
      value={draft[spec.code] ?? ""}
      error={errors[spec.code]}
      onChange={(value) => {
        onChange(spec.code, value);
      }}
    />
  );
  const visible = (spec: ProfileFieldResponse) => spec.required || TEXTILE_MAIN.has(spec.code);
  const optional = fields.filter((spec) => !visible(spec));
  const openAtStart = optional.some(
    (spec) => (draft[spec.code] ?? "") !== "" || errors[spec.code] !== undefined,
  );
  return (
    <>
      {fields.filter(visible).map(input)}
      {main}
      <Disclosure defaultOpen={openAtStart}>
        <div className="flex flex-col gap-4">
          {optional.map(input)}
          {extra}
        </div>
      </Disclosure>
    </>
  );
}
