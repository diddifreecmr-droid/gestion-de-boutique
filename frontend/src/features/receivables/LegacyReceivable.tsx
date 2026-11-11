import { useState } from "react";
import { ArrowLeft, Check } from "lucide-react";
import { uuidV7 } from "../../core/api/uuidv7";
import { useReceivablesDeps } from "../../core/gateways/httpReceivables";
import { ActionBar, AmountField, Button, ChoiceChips, TextField, useToast } from "../../shared/ui";
import { businessDate } from "../expenses/businessDay";
import { FormMessage } from "../expenses/FormMessage";
import { CustomerPicker } from "../sales/CustomerPicker";
import { emptyLegacy, legacyBody, legacyProblems, type LegacyDraft } from "./legacyDraft";
import type { ScreenProps } from "./receivablesNav";
import { sellers } from "./references";
import { useAction } from "./useAction";

const NONE = "none";

/** « Créance ancienne » (UC-CRE-02, propriétaire) : reprise d'une dette de l'ancien cahier. */
export function LegacyReceivable({ shopId, refs, nav }: ScreenProps) {
  const { gateway, now } = useReceivablesDeps();
  const toast = useToast();
  const today = businessDate(now());
  const [draft, setDraft] = useState<LegacyDraft>(emptyLegacy);
  const [showErrors, setShowErrors] = useState(false);
  const [clientId] = useState(uuidV7);
  const action = useAction();
  const update = (patch: Partial<LegacyDraft>) => {
    setDraft((current) => ({ ...current, ...patch }));
  };
  const problems = legacyProblems(draft, today);
  const shown = showErrors ? problems : {};
  const sellerOptions = [
    { value: NONE, label: "Aucun" },
    ...sellers(refs).map((member) => ({ value: member.user_id, label: member.name })),
  ];

  const submit = async () => {
    setShowErrors(true);
    if (Object.keys(problems).length > 0) return;
    await action.run(async () => {
      const created = await gateway.recordLegacy(shopId, legacyBody(draft, clientId));
      toast.show({
        tone: "success",
        message: `Créance ancienne de ${created.customer.name} enregistrée`,
      });
      nav.open(created.id);
    });
  };

  return (
    <>
      <Button variant="ghost" icon={ArrowLeft} onClick={nav.list}>
        Retour aux créances
      </Button>
      <h1 className="m-0 text-title font-bold text-text">Créance ancienne</h1>
      <CustomerPicker
        shopId={shopId}
        title="Client"
        value={draft.customer}
        errors={{ customer: shown.customer, name: shown.name, phone: shown.phone }}
        onChange={(customer) => {
          update({ customer });
        }}
      />
      <AmountField
        label="Montant dû aujourd'hui"
        value={draft.amount}
        error={shown.amount}
        onChange={(amount) => {
          update({ amount });
        }}
      />
      <TextField
        label="Date d'origine"
        type="date"
        max={today}
        value={draft.openedOn}
        error={shown.date}
        onChange={(event) => {
          update({ openedOn: event.target.value });
        }}
      />
      <TextField
        label="Description"
        hint="Ex. « 1 moto Haojue, cahier 2026 »"
        maxLength={500}
        value={draft.description}
        error={shown.description}
        onChange={(event) => {
          update({ description: event.target.value });
        }}
      />
      <ChoiceChips
        label="Vendeur responsable (facultatif)"
        options={sellerOptions}
        value={draft.sellerId ?? NONE}
        onChange={(value) => {
          update({ sellerId: value === NONE ? null : value });
        }}
      />
      <TextField
        label="Conditions (facultatif)"
        maxLength={500}
        value={draft.terms}
        onChange={(event) => {
          update({ terms: event.target.value });
        }}
      />
      {action.message !== null && <FormMessage text={action.message} />}
      <div className="sticky bottom-16 z-20 -mx-4">
        <ActionBar fixed={false}>
          <Button
            size="lg"
            fullWidth
            icon={Check}
            loading={action.busy}
            onClick={() => void submit()}
          >
            Enregistrer la créance
          </Button>
        </ActionBar>
      </div>
    </>
  );
}
