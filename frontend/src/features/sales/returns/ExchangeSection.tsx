import { useId, useState } from "react";
import { Plus } from "lucide-react";
import { formatMoney } from "../../../shared/format";
import { Button, ChoiceChips } from "../../../shared/ui";
import { ArticlePicker } from "../ArticlePicker";
import { newLine, type SaleDraft } from "../draft";
import { SaleLineCard } from "../SaleLineCard";
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
}

/**
 * Échange (UC-VEN-09) : la nouvelle vente se compose avec les cartes de « Nouvelle vente »
 * (article, quantité, prix, détails), au lieu de la vente d'origine. L'avoir lui est versé :
 * seule la différence est payée par le client, ou lui est rendue.
 */
export function ExchangeSection(props: ExchangeSectionProps) {
  const { shopId, location, modes, draft, checks, showErrors, update } = props;
  const titleId = useId();
  const [picking, setPicking] = useState(false);
  const sale = draft.exchange;
  const setSale = (patch: Partial<SaleDraft>) => {
    update({ exchange: { ...sale, ...patch } });
  };
  const { applied, toPay, toGive } = checks.balance;
  const showPicker = picking || sale.lines.length === 0;
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-4">
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Nouvelle vente de l'échange
      </h2>
      {sale.lines.map((line) => (
        <SaleLineCard
          key={line.key}
          line={line}
          locationName={location.name}
          issues={checks.exchange.lines[line.key]}
          showErrors={showErrors}
          onChange={(next) => {
            setSale({ lines: sale.lines.map((l) => (l.key === line.key ? next : l)) });
          }}
          onRemove={() => {
            setSale({ lines: sale.lines.filter((l) => l.key !== line.key) });
          }}
        />
      ))}
      {showErrors && checks.exchangeLines !== undefined && (
        <p className="m-0 text-body text-danger-text">{checks.exchangeLines}</p>
      )}
      {showPicker ? (
        <ArticlePicker
          shopId={shopId}
          locationId={location.id}
          locationName={location.name}
          excluded={sale.lines.map((line) => line.article.id)}
          onPick={(article) => {
            setSale({ lines: [...sale.lines, newLine(article)] });
            setPicking(false);
          }}
          {...(sale.lines.length > 0
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
