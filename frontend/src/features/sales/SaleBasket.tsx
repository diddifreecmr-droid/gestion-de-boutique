import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "../../shared/ui";
import { ArticlePicker } from "./ArticlePicker";
import { newLine, type LineDraft } from "./draft";
import { isBasket, UNIT_FIELDS, type LineFields } from "./lineFields";
import type { LineIssues } from "./saleChecks";
import { SaleLineCard } from "./SaleLineCard";
import { SaleLineSummary } from "./SaleLineSummary";

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
}

function hasError(issues: LineIssues | undefined): boolean {
  return issues?.price !== undefined || (issues?.chassis.some((e) => e !== undefined) ?? false);
}

/**
 * Lignes de la vente et recherche d'article. Panier à la ligne (Prêt-à-porter, § 7.4) : un
 * article peut revenir (autre taille, autre couleur) tant qu'il en reste ; seule la dernière
 * ligne ajoutée est ouverte, les autres se replient (une ligne en erreur reste ouverte).
 */
export function SaleBasket(props: SaleBasketProps) {
  const { shopId, location, lines, issues, showErrors, onLines, searchHint } = props;
  const { fields = UNIT_FIELDS, removeLast = false } = props;
  const basket = isBasket(fields);
  const [picking, setPicking] = useState(false);
  const [openKey, setOpenKey] = useState<string | null>(lines.at(-1)?.key ?? null);
  const showPicker = picking || lines.length === 0;
  const takenBy = (article: string, except: string) =>
    lines
      .filter((l) => l.article.id === article && l.key !== except)
      .reduce((sum, l) => sum + l.quantity, 0);
  const exhausted = lines
    .filter((l) => !basket || takenBy(l.article.id, "") >= l.available)
    .map((l) => l.article.id);

  return (
    <>
      {lines.map((line) => {
        const open = !basket || lines.length === 1 || line.key === openKey;
        if (!open && !(showErrors && hasError(issues[line.key]))) {
          return (
            <SaleLineSummary
              key={line.key}
              line={line}
              onOpen={() => {
                setOpenKey(line.key);
              }}
            />
          );
        }
        return (
          <SaleLineCard
            key={line.key}
            line={line}
            locationName={location.name}
            issues={issues[line.key]}
            showErrors={showErrors}
            fields={fields}
            reserved={basket ? takenBy(line.article.id, line.key) : 0}
            onChange={(next) => {
              onLines(lines.map((l) => (l.key === line.key ? next : l)));
            }}
            {...(basket && lines.length > 1 && line.key === openKey
              ? {
                  onCollapse: () => {
                    setOpenKey(null);
                  },
                }
              : {})}
            {...(removeLast || lines.length > 1
              ? {
                  onRemove: () => {
                    onLines(lines.filter((l) => l.key !== line.key));
                  },
                }
              : {})}
          />
        );
      })}
      {showPicker ? (
        <ArticlePicker
          shopId={shopId}
          locationId={location.id}
          locationName={location.name}
          {...(searchHint === undefined ? {} : { hint: searchHint })}
          excluded={[...new Set(exhausted)]}
          onPick={(article) => {
            const line = newLine(article);
            onLines([...lines, line]);
            setOpenKey(line.key);
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
