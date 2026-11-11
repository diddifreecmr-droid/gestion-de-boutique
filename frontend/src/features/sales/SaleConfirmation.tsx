import { useEffect, useRef } from "react";
import { AlertTriangle, CheckCircle2, CirclePlus, Printer } from "lucide-react";
import type { SaleResult } from "../../core/gateways/salesContract";
import { formatMoney, formatQuantity } from "../../shared/format";
import { ShareButton } from "./ShareButton";
import { warningText } from "./warningText";
import { ActionBar, Badge, Button, ListCard, ListCardRow, SummaryCard } from "../../shared/ui";

export interface SaleConfirmationProps {
  sale: SaleResult;
  /** Ouvre la vue d'impression du reçu (TR-18). */
  onPrint: () => void;
  onNewSale: () => void;
}

/** Écran de confirmation (UC-VEN-01 étape 7) : numéro, total, Imprimer, Partager, Nouvelle vente. */
export function SaleConfirmation({ sale, onPrint, onNewSale }: SaleConfirmationProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    headingRef.current?.focus();
  }, []);
  return (
    <>
      <div className="flex flex-col gap-2">
        <CheckCircle2 aria-hidden="true" className="size-8 text-success-text" />
        <h1
          ref={headingRef}
          tabIndex={-1}
          className="m-0 text-title font-bold text-text outline-hidden"
        >
          Vente enregistrée — reçu n° {sale.number}
        </h1>
        {sale.kind === "credit" && (
          <p className="m-0">
            <Badge status="credit">Vente à crédit</Badge>
          </p>
        )}
      </div>
      {sale.kind === "credit" ? (
        <SummaryCard
          lines={[
            { label: "Total", amount: sale.total },
            { label: "Versé", amount: sale.paid },
          ]}
          due={sale.remaining}
        />
      ) : (
        <p className="m-0 flex items-baseline justify-between gap-4 rounded-lg bg-surface p-4 text-lead shadow-card">
          <span>Total</span>
          <strong className="text-amount tabular-nums">{formatMoney(sale.total)}</strong>
        </p>
      )}
      <ListCard label="Articles vendus">
        {sale.lines.map((line, index) => (
          <ListCardRow
            key={index}
            title={line.article_name}
            subtitle={`${formatQuantity(line.quantity)} × ${formatMoney(line.unit_price)}`}
            amount={line.line_total}
          />
        ))}
      </ListCard>
      {sale.warnings.map((warning, index) => (
        <p
          key={`${warning.code}-${String(index)}`}
          role="status"
          className="m-0 flex items-start gap-2 text-body text-warning-text"
        >
          <AlertTriangle aria-hidden="true" className="size-6 shrink-0" />
          <span>{warningText(warning)}</span>
        </p>
      ))}
      <div className="grid grid-cols-2 gap-4">
        <Button variant="secondary" icon={Printer} fullWidth onClick={onPrint}>
          Imprimer
        </Button>
        <ShareButton />
      </div>
      <div className="sticky bottom-16 z-20 -mx-4">
        <ActionBar fixed={false}>
          <Button size="lg" fullWidth icon={CirclePlus} onClick={onNewSale}>
            Nouvelle vente
          </Button>
        </ActionBar>
      </div>
    </>
  );
}
