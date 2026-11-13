import { useState, type FormEvent } from "react";
import { CirclePlus } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import type {
  ArticleCreateRequest,
  ArticleForm,
  ArticleResponse,
} from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { Button } from "../../shared/ui";
import { ArticleFieldsEditor } from "./ArticleFieldsEditor";
import { catalogRights, type CatalogRole } from "./catalogRights";
import { CreatePriceFields } from "./CreatePriceFields";
import { NO_PRICES } from "./createPrices";
import { ExtraFields } from "./ExtraFields";
import { notesValue, thresholdError, thresholdValue } from "./extraValues";
import { checkDraft, emptyDraft, fieldValues, type FieldDraft } from "./fieldValues";
import { draftName, repeatedNameFix } from "./nameGuard";
import { RepeatedNameNotice } from "./RepeatedNameNotice";
import { SubmitFailureNotice } from "./SubmitFailureNotice";
import { draftPriceLabels, shownFields, textileErrors, withChange } from "./textileFields";
import { useCatalogSubmit } from "./useCatalogSubmit";

export interface ArticleCreateFormProps {
  shopId: string;
  role: CatalogRole;
  form: ArticleForm;
  onCreated: (article: ArticleResponse) => void;
  onOpenExisting: (articleId: string) => void;
}

/**
 * Création : champs obligatoires du profil (Motos : marque + modèle ; Textile : unité, vente à
 * la pièce, longueur), prix pour le propriétaire (UC-STK-01, étape 4), le reste sous « Plus de
 * détails ». Un nom qui répète un mot est signalé avant l'envoi (garde-fou, VOC-04). L'`id`
 * (UUIDv7) est tiré une fois : renvoyer le formulaire après une coupure ne crée pas de doublon.
 */
export function ArticleCreateForm(props: ArticleCreateFormProps) {
  const { shopId, form } = props;
  const gateway = useCatalogAdmin();
  const submit = useCatalogSubmit();
  const [id] = useState(() => uuidV7());
  const [draft, setDraft] = useState<FieldDraft>(() => emptyDraft(form.fields));
  const [extra, setExtra] = useState({ threshold: "", notes: "" });
  const [prices, setPrices] = useState(NO_PRICES);
  const [checked, setChecked] = useState(false);
  /** Nom déjà signalé « mot répété » : un second appui le garde tel quel. */
  const [warnedName, setWarnedName] = useState<string | null>(null);
  const fields = shownFields(form.fields, draft);
  const problems = () => ({ ...checkDraft(fields, draft), ...textileErrors(draft) });
  const errors = checked ? problems() : {};
  const ownerPrices = catalogRights(props.role).setPrices;
  const labels = draftPriceLabels(form.fields, draft);
  const name = draftName(draft);
  const fixed = repeatedNameFix(name);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setChecked(true);
    if (Object.keys(problems()).length > 0 || thresholdError(extra.threshold) !== undefined) return;
    if (fixed !== null && warnedName !== name) {
      setWarnedName(name);
      return;
    }
    const body: ArticleCreateRequest = {
      id,
      fields: fieldValues(fields, draft),
      alert_threshold: thresholdValue(extra.threshold),
      notes: notesValue(extra.notes),
    };
    // Le comptable n'envoie aucun prix : le serveur le refuserait (PRICE_SET, 403).
    if (ownerPrices) {
      body.base_price = prices.base;
      if (form.minPriceEnabled) body.min_price = prices.minimum;
      if (labels.piece !== null) {
        body.base_price_piece = prices.piece;
        if (form.minPriceEnabled) body.min_price_piece = prices.minimumPiece;
      }
    }
    void submit.run(() => gateway.createArticle(shopId, body), props.onCreated);
  }

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
          setDraft((current) => withChange(current, code, value));
        }}
        main={
          ownerPrices && (
            <CreatePriceFields
              labels={labels}
              minPriceEnabled={form.minPriceEnabled}
              value={prices}
              onChange={setPrices}
            />
          )
        }
        extra={<ExtraFields draft={extra} onChange={setExtra} />}
      />
      {fixed !== null && warnedName === name && (
        <RepeatedNameNotice
          name={name}
          fixed={fixed}
          {...("name" in draft
            ? {
                onUse: () => {
                  setDraft((current) => ({ ...current, name: fixed }));
                },
              }
            : {})}
        />
      )}
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
