import { useEffect, useRef } from "react";
import { CheckCircle2, CirclePlus, FileText } from "lucide-react";
import type { Purchase } from "../../core/gateways/purchasingContract";
import { formatMoney } from "../../shared/format";
import { ActionBar, Button } from "../../shared/ui";

export interface PurchaseConfirmationProps {
  purchase: Purchase;
  onOpen: () => void;
  onNew: () => void;
}

/** Confirmation (CDC § 1.3) : « Achat enregistré — A-000012 », total, et « Nouvel achat ». */
export function PurchaseConfirmation({ purchase, onOpen, onNew }: PurchaseConfirmationProps) {
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
          Achat enregistré — <span className="font-mono">{purchase.number}</span>
        </h1>
      </div>
      <p className="m-0 flex flex-wrap items-baseline justify-between gap-4 rounded-lg bg-surface p-4 text-lead shadow-card">
        <span>Total de l'achat</span>
        <strong className="text-amount tabular-nums">{formatMoney(purchase.total)}</strong>
      </p>
      <Button variant="secondary" icon={FileText} fullWidth onClick={onOpen}>
        Voir l'achat
      </Button>
      <div className="sticky bottom-16 z-20 -mx-4">
        <ActionBar fixed={false}>
          <Button size="lg" fullWidth icon={CirclePlus} onClick={onNew}>
            Nouvel achat
          </Button>
        </ActionBar>
      </div>
    </>
  );
}
