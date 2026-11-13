import { useState, type FormEvent } from "react";
import { CirclePlus } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import type {
  ArticleCreateRequest,
  ArticleForm,
  ArticleResponse,
} from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { AmountField, Button } from "../../shared/ui";
import { ArticleFieldsEditor } from "./ArticleFieldsEditor";
import { catalogRights, type CatalogRole } from "./catalogRights";
import { ExtraFields } from "./ExtraFields";
import { notesValue, thresholdError, thresholdValue } from "./extraValues";
import { checkDraft, emptyDraft, fieldValues } from "./fieldValues";
import { SubmitFailureNotice } from "./SubmitFailureNotice";
import { useCatalogSubmit } from "./useCatalogSubmit";

export interface ArticleCreateFormProps {
  shopId: string;
  role: CatalogRole;
  form: ArticleForm;
  onCreated: (article: ArticleResponse) => void;
  onOpenExisting: (articleId: string) => void;
}

/**
 * Création : champs obligatoires du profil (Motos : marque + modèle), prix de base pour le
 * propriétaire (UC-STK-01, étape 4), le reste sous « Plus de détails ». L'`id` (UUIDv7) est
 * tiré une fois : renvoyer le formulaire après une coupure ne crée pas de second article.
 */
export function ArticleCreateForm(props: ArticleCreateFormProps) {
  const { shopId, form } = props;
  const gateway = useCatalogAdmin();
  const submit = useCatalogSubmit();
  const [id] = useState(() => uuidV7());
  const [draft, setDraft] = useState(() => emptyDraft(form.fields));
  const [extra, setExtra] = useState({ threshold: "", notes: "" });
  const [base, setBase] = useState<number | null>(null);
  const [minimum, setMinimum] = useState<number | null>(null);
  const [checked, setChecked] = useState(false);
  const errors = checked ? checkDraft(form.fields, draft) : {};
  const ownerPrices = catalogRights(props.role).setPrices;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setChecked(true);
    const invalid = Object.keys(checkDraft(form.fields, draft)).length > 0;
    if (invalid || thresholdError(extra.threshold) !== undefined) return;
    const body: ArticleCreateRequest = {
      id,
      fields: fieldValues(form.fields, draft),
      alert_threshold: thresholdValue(extra.threshold),
      notes: notesValue(extra.notes),
    };
    // Le comptable n'envoie aucun prix : le serveur le refuserait (PRICE_SET, 403).
    if (ownerPrices) {
      body.base_price = base;
      if (form.minPriceEnabled) body.min_price = minimum;
    }
    void submit.run(() => gateway.createArticle(shopId, body), props.onCreated);
  }

  const prices = ownerPrices && (
    <>
      <AmountField
        label="Prix de base (facultatif)"
        hint="Vide : le prix sera tapé à chaque vente"
        value={base}
        onChange={setBase}
      />
      {form.minPriceEnabled && (
        <AmountField label="Prix minimum (facultatif)" value={minimum} onChange={setMinimum} />
      )}
    </>
  );

  return (
    <form
      noValidate
      aria-label="Nouvel article"
      className="flex flex-col gap-4"
      onSubmit={onSubmit}
    >
      <ArticleFieldsEditor
        fields={form.fields}
        draft={draft}
        errors={errors}
        onChange={(code, value) => {
          setDraft((current) => ({ ...current, [code]: value }));
        }}
        main={prices}
        extra={<ExtraFields draft={extra} onChange={setExtra} />}
      />
      {submit.failure !== null && (
        <SubmitFailureNotice
          failure={submit.failure}
          onOpenExisting={props.onOpenExisting}
          onReload={() => {
            throw new Error("Une création ne peut pas produire de conflit de version");
          }}
        />
      )}
      <Button type="submit" size="lg" fullWidth icon={CirclePlus} loading={submit.pending}>
        Créer l'article
      </Button>
    </form>
  );
}
