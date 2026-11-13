import { formatMoney, formatQuantity } from "../../shared/format";
import { ListCard, ListCardRow } from "../../shared/ui";
import { articleTitle } from "./articleTitle";
import type { LineDraft } from "./draft";
import { attributesText } from "./lineFields";
import { lineTotal } from "./saleChecks";

/**
 * Ligne repliée du panier (design-system § 7.4) : nom, taille · couleur, quantité × prix et
 * total de la ligne ; un appui la rouvre.
 */
export function SaleLineSummary({ line, onOpen }: { line: LineDraft; onOpen: () => void }) {
  const title = articleTitle(line.article.name);
  const attributes = attributesText(line);
  const price = line.unitPrice === null ? "prix vide" : formatMoney(line.unitPrice);
  const each = `${formatQuantity(line.quantity)} × ${price}`;
  return (
    <ListCard label={`Ligne repliée : ${title}`}>
      <ListCardRow
        title={title}
        subtitle={attributes === "" ? each : `${attributes} — ${each}`}
        amount={lineTotal(line)}
        onOpen={onOpen}
      />
    </ListCard>
  );
}
