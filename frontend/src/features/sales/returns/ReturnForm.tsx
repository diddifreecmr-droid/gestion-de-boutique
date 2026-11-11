import { useState } from "react";
import { Check } from "lucide-react";
import { useGateways } from "../../../core/gateways/gateways";
import type { SaleReturn, SaleReturns } from "../../../core/gateways/returnsContract";
import type { SaleResult } from "../../../core/gateways/salesContract";
import { ActionBar, Button, ChoiceChips, TextField } from "../../../shared/ui";
import { FormAlert } from "../../auth/FormAlert";
import { asError } from "../asError";
import { buildReturn } from "./buildReturn";
import { ExchangeSection } from "./ExchangeSection";
import { RefundSection } from "./RefundSection";
import { checkReturn, newReturnDraft, type ReturnDraft, type ReturnKind } from "./returnDraft";
import { returnErrorMessage } from "./returnErrorMessage";
import { ReturnLinesSection } from "./ReturnLinesSection";

export interface ReturnFormProps {
  shopId: string;
  sale: SaleResult;
  listing: SaleReturns;
  location: { id: string; name: string };
  modes: readonly { id: string; name: string }[];
  onDone: (made: SaleReturn) => void;
}

const KINDS = [
  { value: "refund", label: "Retour simple" },
  { value: "exchange", label: "Échange" },
] as const satisfies readonly { value: ReturnKind; label: string }[];

export const FIX_RETURN = "Le retour n'est pas enregistré : corrigez les champs signalés.";

/** Retour ou échange d'une vente (UC-VEN-09, propriétaire) : lignes, motif, remboursement. */
export function ReturnForm({ shopId, sale, listing, location, modes, onDone }: ReturnFormProps) {
  const { sales } = useGateways();
  const [draft, setDraft] = useState<ReturnDraft>(() => newReturnDraft(modes[0]?.id ?? null));
  const [showErrors, setShowErrors] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  const update = (patch: Partial<ReturnDraft>) => {
    setDraft((current) => ({ ...current, ...patch }));
  };
  const checks = checkReturn(sale, listing, draft);

  const submit = async () => {
    if (submitting) return;
    setShowErrors(true);
    if (checks.blocking) {
      setMessage(FIX_RETURN);
      return;
    }
    setMessage(null);
    setSubmitting(true);
    try {
      onDone(await sales.recordReturn(shopId, sale.id, buildReturn(sale, listing, draft, checks)));
    } catch (error) {
      try {
        setMessage(returnErrorMessage(error, draft.exchange.lines, location.name));
      } catch (unexpected) {
        setFatal(unexpected);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const sectionProps = { modes, draft, checks, showErrors, update };
  return (
    <>
      <ReturnLinesSection
        sale={sale}
        listing={listing}
        picks={draft.picks}
        errors={showErrors ? checks.chassis : {}}
        linesError={showErrors ? checks.lines : undefined}
        onChange={(line, pick) => {
          update({ picks: { ...draft.picks, [line]: pick } });
        }}
      />
      <TextField
        label="Motif du retour"
        value={draft.reason}
        error={showErrors ? checks.reason : undefined}
        onChange={(event) => {
          update({ reason: event.target.value });
        }}
      />
      <ChoiceChips
        label="Type de retour"
        options={KINDS}
        value={draft.kind}
        onChange={(kind) => {
          update({ kind });
        }}
      />
      {draft.kind === "refund" ? (
        <RefundSection sale={sale} {...sectionProps} />
      ) : (
        <ExchangeSection shopId={shopId} location={location} {...sectionProps} />
      )}
      <FormAlert message={message} />
      <div className="sticky bottom-16 z-20 -mx-4">
        <ActionBar fixed={false}>
          <Button
            size="lg"
            fullWidth
            icon={Check}
            loading={submitting}
            onClick={() => void submit()}
          >
            {draft.kind === "refund" ? "Enregistrer le retour" : "Enregistrer l'échange"}
          </Button>
        </ActionBar>
      </div>
    </>
  );
}
