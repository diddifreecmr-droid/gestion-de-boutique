import { useState } from "react";
import { Check } from "lucide-react";
import { useGateways } from "../../../core/gateways/gateways";
import type { SaleReturn, SaleReturns } from "../../../core/gateways/returnsContract";
import type { SaleResult } from "../../../core/gateways/salesContract";
import { ActionBar, Button, ChoiceChips, ConfirmDialog, TextField } from "../../../shared/ui";
import { FormAlert } from "../../auth/FormAlert";
import { asError } from "../asError";
import { UNIT_FIELDS, type LineFields } from "../lineFields";
import type { SaleRole } from "../salesNav";
import { buildReturn } from "./buildReturn";
import { ExchangeSection } from "./ExchangeSection";
import {
  deadlineText,
  LATE_CONFIRM_TEXT,
  LATE_CONFIRM_TITLE,
  type ExchangeAccess,
} from "./exchangeRules";
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
  /** Employé : échange seulement (le retour simple reste au propriétaire). */
  role?: SaleRole;
  /** Champs d'une ligne de la nouvelle vente (taille, couleur ou détails). */
  lineFields?: LineFields;
  /** Délai d'échange de la vente (QC-4) ; sans délai par défaut. */
  access?: ExchangeAccess;
  onDone: (made: SaleReturn) => void;
}

const KINDS = [
  { value: "refund", label: "Retour simple" },
  { value: "exchange", label: "Échange" },
] as const satisfies readonly { value: ReturnKind; label: string }[];

export const FIX_RETURN = "Le retour n'est pas enregistré : corrigez les champs signalés.";

const OPEN: ExchangeAccess = { kind: "open", deadline: null, late: false };

/**
 * Retour ou échange d'une vente (UC-VEN-09) : lignes, motif, remboursement ou nouvelle vente.
 * Propriétaire hors délai : l'échange se confirme (« inscrit au journal ») avant l'envoi.
 */
export function ReturnForm(props: ReturnFormProps) {
  const { shopId, sale, listing, location, modes, onDone } = props;
  const { role = "owner", lineFields = UNIT_FIELDS, access = OPEN } = props;
  const exchangeOnly = role !== "owner";
  const { sales } = useGateways();
  const [draft, setDraft] = useState<ReturnDraft>(() => ({
    ...newReturnDraft(modes[0]?.id ?? null),
    ...(exchangeOnly ? { kind: "exchange" as const } : {}),
  }));
  const [showErrors, setShowErrors] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [confirmLate, setConfirmLate] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);
  const update = (patch: Partial<ReturnDraft>) => {
    setDraft((current) => ({ ...current, ...patch }));
  };
  const checks = checkReturn(sale, listing, draft, role);
  const late = draft.kind === "exchange" && access.kind === "open" && access.late;
  const deadline = draft.kind === "exchange" ? deadlineText(access) : null;

  const send = async () => {
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
  const submit = () => {
    if (submitting) return;
    setShowErrors(true);
    if (checks.blocking) {
      setMessage(FIX_RETURN);
      return;
    }
    if (late) setConfirmLate(true);
    else void send();
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
        label={exchangeOnly ? "Motif de l'échange" : "Motif du retour"}
        value={draft.reason}
        error={showErrors ? checks.reason : undefined}
        onChange={(event) => {
          update({ reason: event.target.value });
        }}
      />
      {!exchangeOnly && (
        <ChoiceChips
          label="Type de retour"
          options={KINDS}
          value={draft.kind}
          onChange={(kind) => {
            update({ kind });
          }}
        />
      )}
      {deadline !== null && <p className="m-0 text-body text-text-muted">{deadline}</p>}
      {draft.kind === "refund" ? (
        <RefundSection sale={sale} {...sectionProps} />
      ) : (
        <ExchangeSection
          shopId={shopId}
          location={location}
          lineFields={lineFields}
          {...sectionProps}
        />
      )}
      <FormAlert message={message} />
      <div className="sticky bottom-16 z-20 -mx-4">
        <ActionBar fixed={false}>
          <Button size="lg" fullWidth icon={Check} loading={submitting} onClick={submit}>
            {draft.kind === "refund" ? "Enregistrer le retour" : "Enregistrer l'échange"}
          </Button>
        </ActionBar>
      </div>
      <ConfirmDialog
        open={confirmLate}
        title={LATE_CONFIRM_TITLE}
        confirmLabel="Échanger hors délai"
        onConfirm={() => {
          setConfirmLate(false);
          void send();
        }}
        onCancel={() => {
          setConfirmLate(false);
        }}
      >
        {LATE_CONFIRM_TEXT}
      </ConfirmDialog>
    </>
  );
}
