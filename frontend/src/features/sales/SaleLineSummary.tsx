import { formatMoney, formatQuantity } from "../../shared/format";
import { ListCard, ListCardRow } from "../../shared/ui";
import { articleTitle } from "./articleTitle";
import type { LineDraft } from "./draft";
import { attributesText } from "./lineFields";
import { lineTenths } from "./lineQuantity";
import { lineTotal } from "./saleChecks";
import { metersText, piecesText } from "./textile";

/**
 * Ligne repliée du panier (design-system § 7.4) : nom, taille · couleur, quantité × prix et
 * total de la ligne ; un appui la rouvre.
 */
export function SaleLineSummary({ line, onOpen }: { line: LineDraft; onOpen: () => void }) {
  const title = articleTitle(line.article.name);
  const attributes = attributesText(line);
  const price = line.unitPrice === null ? "prix vide" : formatMoney(line.unitPrice);
  const tenths = lineTenths(line);
  const count =
    line.mode === "meter"
      ? tenths === null
        ? "longueur à préciser"
        : metersText(tenths)
      : line.mode === "piece"
        ? piecesText(line.quantity)
        : formatQuantity(line.quantity);
  const each = `${count} × ${price}`;
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
