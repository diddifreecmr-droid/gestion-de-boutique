import { useEffect, useRef } from "react";
import { CheckCircle2, Eye, Printer } from "lucide-react";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import type { InstallmentResult } from "../../core/gateways/receivablesContract";
import { Button, SummaryCard } from "../../shared/ui";
import { ShareButton } from "../sales/ShareButton";
import { StatusBadge } from "./StatusBadge";

export interface InstallmentConfirmationProps {
  shopId: string;
  result: InstallmentResult;
  onPrint: () => void;
  onOpen: () => void;
}

/** Confirmation (UC-CRE-03 étape 4) : numéro R-…, reste à jour, « Imprimer le reçu ». */
export function InstallmentConfirmation(props: InstallmentConfirmationProps) {
  const { shopId, result, onPrint, onOpen } = props;
  const { gateway } = useReceivablesDeps();
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    headingRef.current?.focus();
  }, []);
  const { installment, receivable } = result;
  return (
    <>
      <div className="flex flex-col gap-2">
        <CheckCircle2 aria-hidden="true" className="size-8 text-success-text" />
        <h1
          ref={headingRef}
          tabIndex={-1}
          className="m-0 text-title font-bold text-text outline-hidden"
        >
          Versement enregistré — reçu n° {installment.number}
        </h1>
        <p className="m-0 text-lead break-words text-text">{receivable.customer.name}</p>
        <p className="m-0">
          <StatusBadge status={receivable.status} />
        </p>
      </div>
      <SummaryCard
        lines={[
          { label: "Ce versement", amount: installment.amount },
          { label: "Total déjà versé", amount: receivable.total_paid },
        ]}
        due={receivable.remaining}
      />
      <Button size="lg" fullWidth icon={Printer} onClick={onPrint}>
        Imprimer le reçu
      </Button>
      <ShareButton
        load={async () => ({
          kind: "installment",
          receipt: await gateway.receipt(shopId, installment.id),
        })}
      />
      <Button variant="ghost" icon={Eye} fullWidth onClick={onOpen}>
        Voir la créance
      </Button>
    </>
  );
}
