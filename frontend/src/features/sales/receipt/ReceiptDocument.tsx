import type { Receipt, ReceiptLine } from "../../../core/gateways/salesContract";
import { formatDate, formatMoney, formatTime } from "../../../shared/format";
import { pageRules, printProfileOf } from "./printProfile";

const Rule = () => <hr className="receipt__rule" />;

function Row({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <p className={`receipt__row ${className ?? ""}`}>
      <span>{label}</span>
      <span>{value}</span>
    </p>
  );
}

/** « Couleur : rouge · Châssis : LBX… · Moteur : … · Taille : … » (champs renseignés seuls). */
function detailText(detail: ReceiptLine["details"][number]): string {
  const parts: [string, string | null][] = [
    ["Couleur", detail.color],
    ["Châssis", detail.chassis_number],
    ["Moteur", detail.engine_number],
    ["Taille", detail.size],
  ];
  return parts
    .filter((part): part is [string, string] => part[1] !== null && part[1] !== "")
    .map(([label, value]) => `${label} : ${value}`)
    .join(" · ");
}

function Line({ line }: { line: ReceiptLine }) {
  return (
    <li className="receipt__line">
      <p>{line.article_name}</p>
      {line.details.map((detail, index) => (
        <p key={index} className="receipt__detail">
          {detailText(detail)}
        </p>
      ))}
      <Row
        label={`${line.quantity_label} × ${formatMoney(line.unit_price)}`}
        value={formatMoney(line.line_total)}
      />
    </li>
  );
}

/**
 * Reçu de vente (UC-VEN-04, TR-18, design-system § 10) rendu depuis le DTO du serveur : en-tête
 * de la boutique, identification, client, lignes et détails, totaux et paiements par mode,
 * mentions encadrées, pied. Le DTO ne porte **aucun** coût ni marge : rien à filtrer ici.
 */
export function ReceiptDocument({ receipt }: { receipt: Receipt }) {
  const { header } = receipt;
  const profile = printProfileOf(receipt.printing.receipt_format);
  const number =
    receipt.provisional_number === null
      ? receipt.number
      : `${receipt.number} (provisoire ${receipt.provisional_number})`;
  return (
    <article aria-label="Reçu" className={`receipt receipt--${profile}`}>
      <style>{pageRules(receipt.printing)}</style>
      <div className="receipt__center">
        <h2 className="receipt__shop">{header.shop_name}</h2>
        <p>{header.city}</p>
        {header.address !== null && <p>{header.address}</p>}
        <p>Tél. {header.phone}</p>
        {header.niu !== null && <p>NIU : {header.niu}</p>}
        {header.rccm !== null && <p>RCCM : {header.rccm}</p>}
      </div>
      <Rule />
      <p className="receipt__title receipt__center">{receipt.title}</p>
      <p>N° {number}</p>
      <p>
        Le {formatDate(receipt.sold_at)} à {formatTime(receipt.sold_at)}
      </p>
      <p>Vendeur : {receipt.seller_name}</p>
      {receipt.customer !== null && (
        <p>
          Client : {receipt.customer.name} — {receipt.customer.phone}
        </p>
      )}
      <Rule />
      <ul aria-label="Articles">
        {receipt.lines.map((line, index) => (
          <Line key={index} line={line} />
        ))}
      </ul>
      <Rule />
      <Row label="Total" value={formatMoney(receipt.total)} className="receipt__total" />
      {receipt.payments.map((payment, index) => (
        <Row
          key={index}
          label={`Payé — ${payment.mode_name}${payment.reference === null ? "" : ` (${payment.reference})`}`}
          value={formatMoney(payment.amount)}
        />
      ))}
      {receipt.remaining > 0 && (
        <Row label="Reste à payer" value={formatMoney(receipt.remaining)} />
      )}
      {receipt.mentions.map((mention) => (
        <p key={mention.code} className="receipt__mention">
          {mention.label}
        </p>
      ))}
      {receipt.footer_message !== null && (
        <>
          <Rule />
          <p className="receipt__center">{receipt.footer_message}</p>
        </>
      )}
    </article>
  );
}
