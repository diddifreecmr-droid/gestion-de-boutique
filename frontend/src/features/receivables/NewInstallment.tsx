import { useState, type ReactNode } from "react";
import { ArrowLeft } from "lucide-react";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import type {
  CustomerSummary,
  InstallmentResult,
  Receivable,
} from "../../core/gateways/receivablesContract";
import { Button, SummaryCard } from "../../shared/ui";
import { LoadingOrOffline } from "../expenses/LoadingOrOffline";
import { useLoad } from "../expenses/useLoad";
import { CustomerDebts } from "./CustomerDebts";
import { CustomerSearch } from "./CustomerSearch";
import { InstallmentConfirmation } from "./InstallmentConfirmation";
import { InstallmentForm } from "./InstallmentForm";
import { InstallmentReceiptPrint } from "./InstallmentReceiptPrint";
import type { ScreenProps } from "./receivablesNav";

const TITLE = "Enregistrer un versement";

/** Créance déjà désignée (depuis sa fiche ou une alerte de rappel). */
function KnownReceivable({
  shopId,
  id,
  form,
}: {
  shopId: string;
  id: string;
  form: (receivable: Receivable) => ReactNode;
}) {
  const { gateway } = useReceivablesDeps();
  const loaded = useLoad(id, () => gateway.get(shopId, id));
  if (loaded.status !== "ready") return <LoadingOrOffline title={TITLE} status={loaded.status} />;
  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">{TITLE}</h1>
      <p className="m-0 text-lead break-words text-text">
        {loaded.value.customer.name} — {loaded.value.customer.phone}
      </p>
      {form(loaded.value)}
    </>
  );
}

/**
 * « Enregistrer un versement » (UC-CRE-03) : sur une créance (`?id=`), sinon chercher le
 * client puis choisir sa créance ; confirmation avec « Imprimer le reçu ».
 */
export function NewInstallment({ shopId, refs, nav, id }: ScreenProps & { id: string | null }) {
  const [customer, setCustomer] = useState<CustomerSummary | null>(null);
  const [result, setResult] = useState<InstallmentResult | null>(null);
  const [printing, setPrinting] = useState(false);
  if (result !== null && printing) {
    return (
      <InstallmentReceiptPrint
        shopId={shopId}
        installmentId={result.installment.id}
        onDone={() => {
          setPrinting(false);
        }}
      />
    );
  }
  if (result !== null) {
    return (
      <InstallmentConfirmation
        shopId={shopId}
        result={result}
        onPrint={() => {
          setPrinting(true);
        }}
        onOpen={() => {
          nav.open(result.receivable.id);
        }}
      />
    );
  }
  const form = (receivable: Receivable) => (
    <>
      <SummaryCard
        lines={[
          { label: "Montant initial", amount: receivable.initial_amount },
          { label: "Déjà versé", amount: receivable.total_paid },
        ]}
        due={receivable.remaining}
      />
      <InstallmentForm
        key={receivable.id}
        shopId={shopId}
        refs={refs}
        receivable={receivable}
        onRecorded={setResult}
      />
    </>
  );
  const back = (
    <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
      Retour aux créances
    </Button>
  );
  if (id !== null) {
    return (
      <>
        {back}
        <KnownReceivable shopId={shopId} id={id} form={form} />
      </>
    );
  }
  return (
    <>
      {back}
      <h1 className="m-0 text-title font-bold text-text">{TITLE}</h1>
      {customer === null ? (
        <CustomerSearch shopId={shopId} onPick={setCustomer} />
      ) : (
        <CustomerDebts
          shopId={shopId}
          customer={customer}
          onChangeCustomer={() => {
            setCustomer(null);
          }}
        >
          {form}
        </CustomerDebts>
      )}
    </>
  );
}
