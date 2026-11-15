import { useState } from "react";
import { Plus } from "lucide-react";
import type { SaleShortcut } from "../../core/gateways/catalogContract";
import { Button } from "../../shared/ui";
import { ArticlePicker } from "./ArticlePicker";
import { newLine, type LineDraft } from "./draft";
import { UNIT_FIELDS, type LineFields } from "./lineFields";
import type { LineIssues } from "./saleChecks";
import { SaleLineCard } from "./SaleLineCard";

export interface SaleBasketProps {
  shopId: string;
  location: { id: string; name: string };
  lines: readonly LineDraft[];
  issues: Readonly<Record<string, LineIssues>>;
  showErrors: boolean;
  onLines: (lines: LineDraft[]) => void;
  /** Champs de la ligne selon le profil (Motos par défaut). */
  fields?: LineFields;
  /** Aide de la recherche d'article (selon le profil). */
  searchHint?: string;
  /** La dernière ligne peut-elle être retirée (échange : oui ; nouvelle vente : non) ? */
  removeLast?: boolean;
  /** Raccourcis de longueur du profil (Textile, RG-X05). */
  shortcuts?: readonly SaleShortcut[];
}

/**
 * Lignes de la vente et recherche d'article : une liste d'articles, chacun avec sa quantité et
 * son prix négocié (Prêt-à-porter simplifié, 2026-11-15). Un article déjà dans la vente n'est
 * plus proposé : on change sa quantité.
 */
export function SaleBasket(props: SaleBasketProps) {
  const { shopId, location, lines, issues, showErrors, onLines, searchHint } = props;
  const { fields = UNIT_FIELDS, removeLast = false } = props;
  const [picking, setPicking] = useState(false);
  const showPicker = picking || lines.length === 0;

  return (
    <>
      {lines.map((line) => (
        <SaleLineCard
          key={line.key}
          line={line}
          locationName={location.name}
          issues={issues[line.key]}
          showErrors={showErrors}
          fields={fields}
          shortcuts={props.shortcuts ?? []}
          onChange={(next) => {
            onLines(lines.map((l) => (l.key === line.key ? next : l)));
          }}
          {...(removeLast || lines.length > 1
            ? {
                onRemove: () => {
                  onLines(lines.filter((l) => l.key !== line.key));
                },
              }
            : {})}
        />
      ))}
      {showPicker ? (
        <ArticlePicker
          shopId={shopId}
          locationId={location.id}
          locationName={location.name}
          {...(searchHint === undefined ? {} : { hint: searchHint })}
          excluded={[...new Set(lines.map((l) => l.article.id))]}
          onPick={(article) => {
            onLines([...lines, newLine(article)]);
            setPicking(false);
          }}
          {...(lines.length > 0
            ? {
                onClose: () => {
                  setPicking(false);
                },
              }
            : {})}
        />
      ) : (
        <Button
          variant="secondary"
          icon={Plus}
          fullWidth
          onClick={() => {
            setPicking(true);
          }}
        >
          Ajouter un article
        </Button>
      )}
    </>
  );
}
