import { useState, type ReactNode } from "react";
import { Check, CirclePlus } from "lucide-react";
import type { Supplier } from "../../core/gateways/purchasingContract";
import { formatMoney } from "../../shared/format";
import { ActionBar, Button, Disclosure, TextField } from "../../shared/ui";
import { FormMessage } from "../expenses/FormMessage";
import { CostSummary } from "./CostSummary";
import { draftCosting } from "./draftCosting";
import { draftProblems, emptyLine, hasProblems, type LineDraft, type PurchaseDraft } from "./draft";
import { LineEditor } from "./LineEditor";
import { PriceGapDialog } from "./PriceGapDialog";
import { PurchaseExtras } from "./PurchaseExtras";
import { PurchaseHeader } from "./PurchaseHeader";
import type { References } from "./references";
import { usePurchaseSubmit } from "./usePurchaseSubmit";

export const FIX_FIELDS = "L'achat n'est pas enregistré : corrigez les champs signalés.";
export const REASON_EMPTY = "Le motif de la correction est obligatoire";

export interface PurchaseFormProps {
  shopId: string;
  refs: References;
  title: string;
  intro?: ReactNode;
  initial: PurchaseDraft;
  today: string;
  submitLabel: string;
  /** Correction (UC-ACH-03) : motif obligatoire, lieu enregistré gardé. */
  correction?: { locationId: string } | undefined;
  onSupplierSaved: (supplier: Supplier) => void;
  /** Envoi ; une erreur levée est traduite (écart de prix → confirmation), la saisie reste. */
  onSubmit: (draft: PurchaseDraft, confirmPriceGap: boolean, reason: string) => Promise<void>;
}

/**
 * Saisie d'un achat **sur un seul écran** (CDC § 8, UC-ACH-01) : en-tête, lignes avec leur
 * total aussitôt, « Plus de détails » (frais, facture, photo, note), récapitulatif des coûts,
 * puis Valider. Rien n'est envoyé tant qu'un champ signalé n'est pas corrigé.
 */
export function PurchaseForm(props: PurchaseFormProps) {
  const { refs, today, correction } = props;
  const [draft, setDraft] = useState(props.initial);
  const [reason, setReason] = useState("");
  const [showErrors, setShowErrors] = useState(false);
  const [reveal, setReveal] = useState(0);
  const update = (patch: Partial<PurchaseDraft>) => {
    setDraft((current) => ({ ...current, ...patch }));
  };
  const updateLine = (key: string, patch: Partial<LineDraft>) => {
    setDraft((d) => ({
      ...d,
      lines: d.lines.map((l) => (l.key === key ? { ...l, ...patch } : l)),
    }));
  };
  const problems = draftProblems(draft, today, refs.me.role === "owner");
  const reasonError = correction !== undefined && reason.trim() === "" ? REASON_EMPTY : undefined;
  const submit = usePurchaseSubmit((confirm) => props.onSubmit(draft, confirm, reason.trim()));

  const validate = () => {
    setShowErrors(true);
    // Un frais à corriger est sous « Plus de détails » : on rouvre le panneau pour le montrer.
    if (Object.keys(problems.fees).length > 0) setReveal((n) => n + 1);
    if (hasProblems(problems) || reasonError !== undefined) {
      submit.say(FIX_FIELDS);
      return;
    }
    void submit.run(false);
  };
  const costing = draftCosting(draft);
  const { fees, note, invoiceRef } = props.initial;
  const extrasFilled = fees.length > 0 || note !== "" || invoiceRef !== "";
  const single = draft.lines.length === 1;

  return (
    <>
      <h1 className="m-0 text-title font-bold text-text">{props.title}</h1>
      {props.intro}
      <PurchaseHeader
        shopId={props.shopId}
        refs={refs}
        draft={draft}
        today={today}
        dateError={showErrors ? problems.date : undefined}
        update={update}
        onSupplierSaved={props.onSupplierSaved}
        keepLocationId={correction?.locationId}
      />
      {draft.lines.map((line, index) => (
        <LineEditor
          key={line.key}
          shopId={props.shopId}
          role={refs.me.role}
          index={index}
          line={line}
          problems={problems.lines[line.key]}
          showErrors={showErrors}
          onChange={(patch) => {
            updateLine(line.key, patch);
          }}
          onRemove={
            single
              ? undefined
              : () => {
                  update({ lines: draft.lines.filter((item) => item.key !== line.key) });
                }
          }
        />
      ))}
      <Button
        variant="secondary"
        icon={CirclePlus}
        fullWidth
        onClick={() => {
          update({ lines: [...draft.lines, emptyLine()] });
        }}
      >
        Ajouter une ligne
      </Button>
      <Disclosure key={reveal} defaultOpen={reveal > 0 || extrasFilled}>
        <PurchaseExtras draft={draft} problems={problems} showErrors={showErrors} update={update} />
      </Disclosure>
      <CostSummary draft={draft} />
      {correction !== undefined && (
        <TextField
          label="Motif de la correction"
          required
          maxLength={500}
          value={reason}
          error={showErrors ? reasonError : undefined}
          onChange={(event) => {
            setReason(event.target.value);
          }}
        />
      )}
      {submit.message !== null && <FormMessage text={submit.message} />}
      <PriceGapDialog
        gaps={submit.gaps}
        draft={draft}
        onConfirm={() => void submit.run(true)}
        onCancel={submit.dismissGaps}
      />
      <div className="sticky bottom-16 z-20 -mx-4">
        <ActionBar
          fixed={false}
          summary={costing === null ? undefined : `Total ${formatMoney(costing.costing.total)}`}
        >
          <Button size="lg" fullWidth icon={Check} loading={submit.pending} onClick={validate}>
            {props.submitLabel}
          </Button>
        </ActionBar>
      </div>
    </>
  );
}
