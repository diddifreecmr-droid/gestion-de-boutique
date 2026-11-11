import { useState } from "react";
import { Camera, Check } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import { useStockGateway } from "../../core/gateways/httpStock";
import type { StockColumn, StockRow } from "../../core/gateways/stockContract";
import { Button, ChoiceChips, Disclosure, TextField, useToast } from "../../shared/ui";
import {
  checkDraft,
  CONDITIONS,
  DIRECTIONS,
  reasonsFor,
  type AdjustmentDraft,
  type DraftErrors,
} from "./adjustmentRules";
import { ArticleChooser } from "./ArticleChooser";
import { ErrorText } from "./Notice";
import { failureText } from "./stockErrors";
import { quantityHint, quantityText } from "./quantities";
import { useStockSubmit } from "./useStockSubmit";

export interface AdjustmentFormProps {
  shopId: string;
  locations: readonly StockColumn[];
  articles: readonly StockRow[];
  preselected: StockRow | null;
  /** Ajustement enregistré : ouvre l'historique de l'article. */
  onDone: (articleId: string) => void;
}

/** Formulaire de l'ajustement : lieu, article, sens, quantité, état, motif, note, photo. */
export function AdjustmentForm({
  shopId,
  locations,
  articles,
  preselected,
  onDone,
}: AdjustmentFormProps) {
  const gateway = useStockGateway();
  const toast = useToast();
  /** Identifiant fixé à l'ouverture : un double envoi est rejoué sans doublon (specs § 6.1). */
  const [id] = useState(() => uuidV7());
  const [article, setArticle] = useState<StockRow | null>(preselected);
  const [draft, setDraft] = useState<Omit<AdjustmentDraft, "articleId" | "unit">>({
    locationId: locations[0]?.location_id ?? null,
    direction: "out",
    condition: "sellable",
    quantity: "",
    reason: null,
    note: "",
  });
  const [errors, setErrors] = useState<DraftErrors>({});
  const location = locations.find((place) => place.location_id === draft.locationId) ?? null;
  const submit = useStockSubmit(location?.name ?? "");
  const full: AdjustmentDraft = {
    ...draft,
    articleId: article?.article_id ?? null,
    unit: article?.stock_unit ?? null,
  };
  const patch = (change: Partial<typeof draft>) => {
    setDraft((current) => ({ ...current, ...change }));
  };
  const cell = article?.cells.find((c) => c.location_id === draft.locationId);
  const available =
    article === null || cell === undefined
      ? undefined
      : `Stock vendable ici : ${quantityText(cell.sellable, article.stock_unit)}` +
        ` — abîmé : ${quantityText(cell.damaged, article.stock_unit)}`;

  const send = () => {
    const checked = checkDraft(full, id);
    setErrors(checked.errors);
    const body = checked.body;
    if (body === null) return;
    void submit.run(
      () => gateway.adjust(shopId, body),
      (done) => {
        const after =
          done.balance_after === null || article === null
            ? ""
            : ` — stock après : ${quantityText(done.balance_after, article.stock_unit)}`;
        toast.show({ tone: "success", message: `Ajustement enregistré${after}` });
        onDone(done.article_id);
      },
    );
  };

  const note = (
    <TextField
      label={draft.reason === "other" ? "Note" : "Note (facultative)"}
      value={draft.note}
      error={errors.note}
      maxLength={500}
      onChange={(event) => {
        patch({ note: event.target.value });
      }}
    />
  );
  return (
    <>
      <ChoiceChips
        label="Lieu"
        options={locations.map((place) => ({ value: place.location_id, label: place.name }))}
        value={draft.locationId}
        onChange={(locationId) => {
          patch({ locationId });
        }}
      />
      <ArticleChooser
        articles={articles}
        selected={article}
        onSelect={setArticle}
        error={errors.article}
      />
      {available !== undefined && <p className="m-0 text-body text-text-muted">{available}</p>}
      <ChoiceChips
        label="Sens"
        options={DIRECTIONS}
        value={draft.direction}
        onChange={(direction) => {
          patch({ direction });
        }}
      />
      <TextField
        label="Quantité"
        inputMode="decimal"
        autoComplete="off"
        hint={article === null ? undefined : quantityHint(article.stock_unit)}
        value={draft.quantity}
        error={errors.quantity}
        onChange={(event) => {
          patch({ quantity: event.target.value });
        }}
      />
      <ChoiceChips
        label="État"
        options={CONDITIONS}
        value={draft.condition}
        onChange={(condition) => {
          patch({ condition });
        }}
      />
      <ChoiceChips
        label="Motif"
        options={reasonsFor(article?.stock_unit ?? null)}
        value={draft.reason}
        onChange={(reason) => {
          patch({ reason });
        }}
      />
      {errors.reason !== undefined && <ErrorText text={errors.reason} />}
      {draft.reason === "other" && note}
      <Disclosure>
        {draft.reason !== "other" && note}
        <Button
          variant="secondary"
          fullWidth
          icon={Camera}
          disabledReason="Pièces jointes : à venir"
        >
          Ajouter une photo
        </Button>
      </Disclosure>
      {submit.failure !== null && <ErrorText text={failureText(submit.failure)} />}
      <Button size="lg" fullWidth icon={Check} loading={submit.pending} onClick={send}>
        Enregistrer l'ajustement
      </Button>
    </>
  );
}
