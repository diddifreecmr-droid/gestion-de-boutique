import { useState, type FormEvent } from "react";
import { Save, X } from "lucide-react";
import type {
  ArticlePatchRequest,
  ArticleResponse,
  ProfileFieldResponse,
} from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { Button, TextField } from "../../shared/ui";
import { ArticleFieldsEditor } from "./ArticleFieldsEditor";
import type { ArticleView } from "./articleView";
import { ExtraFields } from "./ExtraFields";
import { notesValue, thresholdError, thresholdValue } from "./extraValues";
import { changedValues, checkDraft, draftOf } from "./fieldValues";
import { InlineMessage } from "./InlineMessage";
import { shownFields, textileErrors, withChange } from "./textileFields";
import { SubmitFailureNotice } from "./SubmitFailureNotice";
import { useCatalogSubmit } from "./useCatalogSubmit";

export interface ArticleEditFormProps {
  shopId: string;
  view: ArticleView;
  fields: readonly ProfileFieldResponse[];
  onSaved: (article: ArticleResponse) => void;
  onCancel: () => void;
  onOpenExisting: (articleId: string) => void;
  onReload: () => void;
}

export const NOTHING_CHANGED = "Aucun changement à enregistrer.";

/** UC-STK-02 : champs du profil, seuil, notes ; `version` lue ; motif facultatif. */
export function ArticleEditForm(props: ArticleEditFormProps) {
  const { shopId, view, fields } = props;
  const gateway = useCatalogAdmin();
  const submit = useCatalogSubmit();
  const initial = draftOf(fields, view.values);
  const [draft, setDraft] = useState(initial);
  const [extra, setExtra] = useState({
    threshold: view.alertThreshold ?? "",
    notes: view.notes ?? "",
  });
  const [reason, setReason] = useState("");
  const [checked, setChecked] = useState(false);
  const [unchanged, setUnchanged] = useState(false);
  const problems = () => ({
    ...checkDraft(shownFields(fields, draft), draft),
    ...textileErrors(draft),
  });
  const errors = checked ? problems() : {};

  function patch(): ArticlePatchRequest | null {
    const changed = changedValues(fields, initial, draft);
    const body: ArticlePatchRequest = { version: view.version, fields: changed };
    const threshold = thresholdValue(extra.threshold);
    if (threshold !== view.alertThreshold) body.alert_threshold = threshold;
    const notes = notesValue(extra.notes);
    if (notes !== view.notes) body.notes = notes;
    const motive = reason.trim();
    if (motive !== "") body.reason = motive;
    const empty = Object.keys(changed).length === 0 && !("alert_threshold" in body);
    return empty && !("notes" in body) ? null : body;
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setChecked(true);
    const invalid = Object.keys(problems()).length > 0;
    if (invalid || thresholdError(extra.threshold) !== undefined) return;
    const body = patch();
    setUnchanged(body === null);
    if (body === null) return;
    void submit.run(() => gateway.updateArticle(shopId, view.id, body), props.onSaved);
  }

  return (
    <form
      noValidate
      aria-label="Modifier l'article"
      className="flex flex-col gap-4"
      onSubmit={onSubmit}
    >
      <h2 className="m-0 text-title-sm font-semibold text-text">Modifier l'article</h2>
      <ArticleFieldsEditor
        fields={fields}
        draft={draft}
        errors={errors}
        onChange={(code, value) => {
          setDraft((current) => withChange(current, code, value));
        }}
        extra={<ExtraFields draft={extra} onChange={setExtra} />}
      />
      <TextField
        label="Motif (facultatif)"
        hint="Gardé au journal avec l'ancienne et la nouvelle valeur"
        autoComplete="off"
        value={reason}
        onChange={(event) => {
          setReason(event.target.value);
        }}
      />
      {unchanged && <InlineMessage text={NOTHING_CHANGED} />}
      {submit.failure !== null && (
        <SubmitFailureNotice
          failure={submit.failure}
          onOpenExisting={props.onOpenExisting}
          onReload={props.onReload}
        />
      )}
      <Button type="submit" size="lg" fullWidth icon={Save} loading={submit.pending}>
        Enregistrer
      </Button>
      <Button variant="ghost" fullWidth icon={X} onClick={props.onCancel}>
        Annuler la modification
      </Button>
    </form>
  );
}
