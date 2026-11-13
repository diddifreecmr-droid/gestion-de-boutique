import { useState, type FormEvent } from "react";
import { Save, X } from "lucide-react";
import type { ArticleResponse } from "../../core/gateways/catalogAdminContract";
import { useCatalogAdmin } from "../../core/gateways/catalogAdminContext";
import { AmountField, Button } from "../../shared/ui";
import type { OwnerArticle } from "./articleView";
import { SubmitFailureNotice } from "./SubmitFailureNotice";
import { useCatalogSubmit } from "./useCatalogSubmit";

export interface PricesFormProps {
  shopId: string;
  article: OwnerArticle;
  /** Réglage « prix minimum » de la boutique (H9) : le champ n'apparaît que s'il est actif. */
  minPriceEnabled: boolean;
  onSaved: (article: ArticleResponse) => void;
  onCancel: () => void;
  onReload: () => void;
}

/**
 * UC-STK-03 (propriétaire seul) : prix de base et prix minimum. `PUT` remplace les quatre
 * prix : ceux qui ne sont pas à l'écran (à la pièce, minimum désactivé) sont renvoyés tels quels.
 */
export function PricesForm(props: PricesFormProps) {
  const { shopId, article, minPriceEnabled } = props;
  const { prices } = article;
  const gateway = useCatalogAdmin();
  const submit = useCatalogSubmit();
  const [base, setBase] = useState<number | null>(prices.basePrice);
  const [minimum, setMinimum] = useState<number | null>(prices.minPrice);
  const showMinimum = minPriceEnabled || prices.minPrice !== null;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const body = {
      version: article.version,
      base_price: base,
      min_price: showMinimum ? minimum : prices.minPrice,
      base_price_piece: prices.basePricePiece,
      min_price_piece: prices.minPricePiece,
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
        label="Prix de base"
        hint="Pré-rempli à chaque vente ; vide : le prix est tapé à chaque vente"
        value={base}
        onChange={setBase}
      />
      {showMinimum && (
        <AmountField
          label="Prix minimum"
          hint="En dessous, la vente demande l'accord du propriétaire"
          value={minimum}
          onChange={setMinimum}
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
