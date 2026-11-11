import { useId, useState } from "react";
import { UserCog, XCircle } from "lucide-react";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import type { Receivable } from "../../core/gateways/receivablesContract";
import { formatMoney } from "../../shared/format";
import { Button, ChoiceChips, ConfirmDialog } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { sellers, type References } from "./references";
import { useAction } from "./useAction";

export interface OwnerActionsProps {
  shopId: string;
  refs: References;
  receivable: Receivable;
  onChanged: (receivable: Receivable) => void;
}

const NONE = "none";

/**
 * Actions du propriétaire (`manageable`) : changer le vendeur responsable (UC-CRE-01) et
 * passer la créance en perte avec un motif (UC-CRE-09, En cours seulement).
 */
export function OwnerActions({ shopId, refs, receivable, onChanged }: OwnerActionsProps) {
  const { gateway } = useReceivablesDeps();
  const titleId = useId();
  const [seller, setSeller] = useState(receivable.responsible_seller_id ?? NONE);
  const [confirming, setConfirming] = useState(false);
  const action = useAction();
  const options = [
    { value: NONE, label: "Aucun" },
    ...sellers(refs).map((member) => ({ value: member.user_id, label: member.name })),
  ];
  const current = receivable.responsible_seller_id ?? NONE;
  if (!options.some((option) => option.value === current)) {
    options.push({ value: current, label: "Vendeur désactivé" });
  }
  const save = () =>
    action.run(async () => {
      const patch = {
        version: receivable.version,
        responsible_seller_id: seller === NONE ? null : seller,
      };
      onChanged(await gateway.change(shopId, receivable.id, patch));
    });
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-2">
      <h2 id={titleId} className="m-0 text-title-sm font-semibold text-text">
        Gestion
      </h2>
      <ChoiceChips
        label="Vendeur responsable"
        options={options}
        value={seller}
        onChange={setSeller}
      />
      {seller !== current && (
        <Button
          variant="secondary"
          icon={UserCog}
          loading={action.busy}
          onClick={() => void save()}
        >
          Changer le vendeur responsable
        </Button>
      )}
      {receivable.status === "open" && (
        <Button
          variant="danger"
          icon={XCircle}
          onClick={() => {
            setConfirming(true);
          }}
        >
          Passer en perte
        </Button>
      )}
      {action.message !== null && <FormMessage text={action.message} />}
      <ConfirmDialog
        open={confirming}
        title={`Passer en perte la créance de ${receivable.customer.name} ?`}
        confirmLabel="Passer en perte"
        confirmIcon={XCircle}
        requireReason
        onCancel={() => {
          setConfirming(false);
        }}
        onConfirm={(reason) => {
          if (reason === null) throw new Error("Mise en perte sans motif");
          setConfirming(false);
          void action.run(async () => {
            onChanged(await gateway.writeOff(shopId, receivable.id, reason));
          });
        }}
      >
        {`${formatMoney(receivable.remaining)} sortent du total à recevoir. Un versement reçu plus tard restera possible (récupération sur perte).`}
      </ConfirmDialog>
    </section>
  );
}
