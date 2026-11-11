import { useState } from "react";
import { ArrowLeft, ScrollText, Wallet } from "lucide-react";
import type { Receivable } from "../../core/gateways/receivablesContract";
import { acceptsPayment } from "./receivableRules";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import { Button } from "../../shared/ui";
import { LoadingOrOffline } from "../expenses/LoadingOrOffline";
import { useLoad } from "../expenses/useLoad";
import { GuarantorsSection } from "./GuarantorsSection";
import { InstallmentReceiptPrint } from "./InstallmentReceiptPrint";
import { InstallmentsSection } from "./InstallmentsSection";
import { OwnerActions } from "./OwnerActions";
import { ReceivableFacts } from "./ReceivableFacts";
import type { ScreenProps } from "./receivablesNav";
import { RemindersSection } from "./RemindersSection";
import { StatusBadge } from "./StatusBadge";

/** Fiche d'une créance : faits, versements, rappels, garants, et actions selon le rôle. */
export function ReceivableDetail({ shopId, refs, nav, id }: ScreenProps & { id: string }) {
  const { gateway } = useReceivablesDeps();
  const loaded = useLoad(id, () => gateway.get(shopId, id));
  const [changed, setChanged] = useState<Receivable | null>(null);
  const [printing, setPrinting] = useState<string | null>(null);
  if (loaded.status !== "ready") return <LoadingOrOffline title="Créance" status={loaded.status} />;
  const receivable = changed ?? loaded.value;
  if (printing !== null) {
    return (
      <InstallmentReceiptPrint
        shopId={shopId}
        installmentId={printing}
        onDone={() => {
          setPrinting(null);
        }}
      />
    );
  }
  const section = { shopId, receivable, onChanged: setChanged };
  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
        Retour aux créances
      </Button>
      <div className="flex flex-col gap-2">
        <h1 className="m-0 text-title font-bold break-words text-text">
          Créance de {receivable.customer.name}
        </h1>
        <p className="m-0">
          <StatusBadge status={receivable.status} />
        </p>
      </div>
      <ReceivableFacts refs={refs} receivable={receivable} />
      {acceptsPayment(receivable) && (
        <Button
          size="lg"
          fullWidth
          icon={Wallet}
          onClick={() => {
            nav.pay(receivable.id);
          }}
        >
          Enregistrer un versement
        </Button>
      )}
      <Button
        variant="secondary"
        icon={ScrollText}
        fullWidth
        onClick={() => {
          nav.statement(receivable.customer.id);
        }}
      >
        Relevé du client
      </Button>
      <InstallmentsSection {...section} refs={refs} onPrint={setPrinting} />
      <RemindersSection {...section} />
      <GuarantorsSection {...section} />
      {receivable.manageable && <OwnerActions {...section} refs={refs} />}
    </>
  );
}
