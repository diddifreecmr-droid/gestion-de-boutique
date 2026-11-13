import { useId } from "react";
import { formatMoney } from "../../../shared/format";
import { ChoiceChips } from "../../../shared/ui";
import { UNIT_FIELDS, type LineFields } from "../lineFields";
import { SaleBasket } from "../SaleBasket";
import { ExchangeCreditFields } from "./ExchangeCreditFields";
import type { ReturnChecks, ReturnDraft } from "./returnDraft";

export interface ExchangeSectionProps {
  shopId: string;
  location: { id: string; name: string };
  modes: readonly { id: string; name: string }[];
  draft: ReturnDraft;
  checks: ReturnChecks;
  showErrors: boolean;
  update: (patch: Partial<ReturnDraft>) => void;
  /** Champs d'une ligne selon le profil (taille, couleur ou détails ; Motos par défaut). */
  lineFields?: LineFields;
}

/**
 * Échange (UC-VEN-09) : la nouvelle vente se compose avec les cartes de « Nouvelle vente »
 * (article, quantité, prix, détails), au lieu de la vente d'origine. L'avoir lui est versé :
 * seule la différence est payée par le client, ou lui est rendue.
 */
export function ExchangeSection(props: ExchangeSectionProps) {
  const { shopId, location, modes, draft, checks, showErrors, update } = props;
  const lineFields = props.lineFields ?? UNIT_FIELDS;
  const titleId = useId();
  const sale = draft.exchange;
  const { applied, toPay, toGive } = checks.balance;
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-4">
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Nouvelle vente de l'échange
      </h2>
      {showErrors && checks.exchangeLines !== undefined && (
        <p className="m-0 text-body text-danger-text">{checks.exchangeLines}</p>
      )}
      <SaleBasket
        shopId={shopId}
        location={location}
        lines={sale.lines}
        issues={checks.exchange.lines}
        showErrors={showErrors}
        fields={lineFields}
        removeLast
        onLines={(lines) => {
          update({ exchange: { ...sale, lines } });
        }}
      />
      <ChoiceChips
        label="Mode de paiement de l'échange"
        options={modes.map((mode) => ({ value: mode.id, label: mode.name }))}
        value={draft.modeId}
        onChange={(modeId) => {
          update({ modeId });
        }}
      />
      {showErrors && checks.mode !== undefined && (
        <p className="m-0 text-body text-danger-text">{checks.mode}</p>
      )}
      <ExchangeCreditFields draft={draft} checks={checks} showErrors={showErrors} update={update} />
      <dl
        aria-label="Différence de l'échange"
        className="m-0 grid grid-cols-2 gap-x-4 gap-y-1 rounded-lg bg-surface p-4 text-body text-text shadow-card"
      >
        <dt className="text-text-muted">Valeur rendue</dt>
        <dd className="m-0 text-right tabular-nums">{formatMoney(checks.value)}</dd>
        {checks.settlement.reduction > 0 && (
          <>
            <dt className="text-text-muted">Baisse de la créance</dt>
            <dd className="m-0 text-right tabular-nums">
              {formatMoney(checks.settlement.reduction)}
            </dd>
          </>
        )}
        <dt className="text-text-muted">Avoir du client</dt>
        <dd className="m-0 text-right tabular-nums">{formatMoney(checks.settlement.refundMax)}</dd>
        <dt className="text-text-muted">Nouvelle vente</dt>
        <dd className="m-0 text-right tabular-nums">{formatMoney(checks.exchange.total)}</dd>
        <dt className="text-text-muted">Avoir utilisé</dt>
        <dd className="m-0 text-right tabular-nums">{formatMoney(applied)}</dd>
        <dt className="font-semibold">
          {toGive > 0 ? "À rendre au client" : "À payer par le client"}
        </dt>
        <dd className="m-0 text-right text-amount font-bold tabular-nums">
          {formatMoney(toGive > 0 ? toGive : toPay)}
        </dd>
      </dl>
    </section>
  );
}
