import type { InstallmentReceipt } from "../../../core/gateways/receivablesContract";
import { formatDate, formatMoney } from "../../../shared/format";
import { pageRules, printProfileOf } from "../../sales/receipt/printProfile";
import { DEFAULT_PRINTING } from "./printing";

function Row({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <p className={`receipt__row ${className ?? ""}`}>
      <span>{label}</span>
      <span>{value}</span>
    </p>
  );
}

/**
 * Reçu de versement (UC-CRE-03 étape 4, design-system § 10) rendu depuis le DTO du serveur :
 * numéro R-…, client, montant, mode, total déjà versé, reste ; « Soldé » si le reste est nul.
 */
export function InstallmentReceiptDocument({ receipt }: { receipt: InstallmentReceipt }) {
  const profile = printProfileOf(DEFAULT_PRINTING.receipt_format);
  const mode =
    receipt.reference === null ? receipt.mode_name : `${receipt.mode_name} (${receipt.reference})`;
  return (
    <article aria-label="Reçu de versement" className={`receipt receipt--${profile}`}>
      <style>{pageRules(DEFAULT_PRINTING)}</style>
      <div className="receipt__center">
        <h2 className="receipt__shop">{receipt.shop_name}</h2>
        {receipt.shop_city !== null && <p>{receipt.shop_city}</p>}
        {receipt.shop_phone !== null && <p>Tél. {receipt.shop_phone}</p>}
      </div>
      <hr className="receipt__rule" />
      <p className="receipt__title receipt__center">Reçu de versement</p>
      <p>N° {receipt.number}</p>
      <p>Le {formatDate(receipt.paid_on)}</p>
      <p>
        Client : {receipt.customer_name} — {receipt.customer_phone}
      </p>
      {receipt.sale_number !== null && <p>Vente : {receipt.sale_number}</p>}
      <hr className="receipt__rule" />
      <Row label="Versement" value={formatMoney(receipt.amount)} className="receipt__total" />
      <Row label="Mode" value={mode} />
      <Row label="Total déjà versé" value={formatMoney(receipt.total_paid)} />
      <Row label="Reste à payer" value={formatMoney(receipt.remaining)} />
      {receipt.nature === "recovery" && <p className="receipt__mention">Récupération sur perte</p>}
      {receipt.settled && <p className="receipt__mention">Soldé</p>}
      {receipt.cancelled && <p className="receipt__mention">Versement annulé</p>}
    </article>
  );
}
