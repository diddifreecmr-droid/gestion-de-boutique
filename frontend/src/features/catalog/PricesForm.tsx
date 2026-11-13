import { useState, type FormEvent } from "react";
import { Save, X } from "lucide-react";
import type { ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { AmountField, Button } from "../../shared/ui";
import type { OwnerArticle } from "./articleView";
import { SubmitFailureNotice } from "./SubmitFailureNotice";
import type { PriceLabels } from "./textileFields";
import { useCatalogSubmit } from "./useCatalogSubmit";

export interface PricesFormProps {
  shopId: string;
  article: OwnerArticle;
  /** « Prix de base », ou « Prix au mètre » et « Prix à la pièce » (Textile). */
  labels: PriceLabels;
  /** Réglage « prix minimum » de la boutique (H9) : le champ n'apparaît que s'il est actif. */
  minPriceEnabled: boolean;
  onSaved: (article: ArticleResponse) => void;
  onCancel: () => void;
  onReload: () => void;
}

const MINIMUM_HINT = "En dessous, la vente demande l'accord du propriétaire";

/**
 * UC-STK-03 (propriétaire seul) : prix de base et prix minimum, et prix à la pièce d'un article
 * Textile vendu à la pièce. `PUT` remplace les quatre prix : ceux qui ne sont pas à l'écran
 * (à la pièce, minimum désactivé) sont renvoyés tels quels.
 */
export function PricesForm(props: PricesFormProps) {
  const { shopId, article, minPriceEnabled, labels } = props;
  const { prices } = article;
  const gateway = useCatalogAdmin();
  const submit = useCatalogSubmit();
  const [base, setBase] = useState<number | null>(prices.basePrice);
  const [minimum, setMinimum] = useState<number | null>(prices.minPrice);
  const [piece, setPiece] = useState<number | null>(prices.basePricePiece);
  const [minimumPiece, setMinimumPiece] = useState<number | null>(prices.minPricePiece);
  const showMinimum = minPriceEnabled || prices.minPrice !== null;
  const byPiece = labels.piece !== null;
  const showMinimumPiece = byPiece && (minPriceEnabled || prices.minPricePiece !== null);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const body = {
      version: article.version,
      base_price: base,
      min_price: showMinimum ? minimum : prices.minPrice,
      base_price_piece: byPiece ? piece : prices.basePricePiece,
      min_price_piece: showMinimumPiece ? minimumPiece : prices.minPricePiece,
    };
    void submit.run(() => gateway.setPrices(shopId, article.id, body), props.onSaved);
  }

  return (
    <form
      noValidate
      aria-label="Modifier les prix"
      className="flex flex-col gap-4"
      onSubmit={onSubmit}
    >
      <h2 className="m-0 text-title-sm font-semibold text-text">Modifier les prix</h2>
      <AmountField
        label={labels.base}
        hint="Pré-rempli à chaque vente ; vide : le prix est tapé à chaque vente"
        value={base}
        onChange={setBase}
      />
      {showMinimum && (
        <AmountField
          label={byPiece ? "Minimum au mètre" : "Prix minimum"}
          hint={MINIMUM_HINT}
          value={minimum}
          onChange={setMinimum}
        />
      )}
      {labels.piece !== null && (
        <AmountField label={labels.piece} value={piece} onChange={setPiece} />
      )}
      {showMinimumPiece && (
        <AmountField
          label="Minimum à la pièce"
          hint={MINIMUM_HINT}
          value={minimumPiece}
          onChange={setMinimumPiece}
        />
      )}
      <p className="m-0 text-body text-text-muted">
        Le nouveau prix vaut pour les ventes suivantes, pas pour les ventes passées.
      </p>
      {submit.failure !== null && (
        <SubmitFailureNotice
          failure={submit.failure}
          onOpenExisting={() => {
            throw new Error("Un changement de prix ne peut pas produire de doublon");
          }}
          onReload={props.onReload}
        />
      )}
      <Button type="submit" size="lg" fullWidth icon={Save} loading={submit.pending}>
        Enregistrer les prix
      </Button>
      <Button variant="ghost" fullWidth icon={X} onClick={props.onCancel}>
        Annuler la modification
      </Button>
    </form>
  );
}
