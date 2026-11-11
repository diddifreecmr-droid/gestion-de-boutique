import { useState } from "react";
import { ApiError, NetworkError } from "../../core/api/errors";
import { uuidV7 } from "../../core/api/uuidv7";
import type { SaleSetup } from "../../core/gateways/catalogContract";
import { useGateways } from "../../core/gateways/gateways";
import { priceBelowMinimum } from "../../core/gateways/saleErrors";
import type { SaleResult } from "../../core/gateways/salesContract";
import { asError } from "./asError";
import { buildCommand } from "./buildCommand";
import { CREDIT_CHOICE, type LineDraft, type SaleDraft } from "./draft";
import { writeLastPaymentMode } from "./lastPaymentMode";
import type { SaleChecks } from "./saleChecks";
import { OFFLINE_MESSAGE, saleErrorMessage } from "./saleErrorMessage";

export const FIX_FIELDS = "La vente n'est pas enregistrée : corrigez les champs signalés.";
export const BELOW_MINIMUM = "Prix inférieur au minimum : validation du propriétaire nécessaire.";

/** Clé d'une demande d'accord : un article à un prix donné (changer le prix l'invalide). */
export function approvalKey(line: LineDraft): string {
  return `${line.article.id}:${String(line.unitPrice)}`;
}

interface Options {
  shopId: string;
  setup: SaleSetup;
  draft: SaleDraft;
  checks: SaleChecks;
  update: (patch: Partial<SaleDraft>) => void;
  onRecorded: (sale: SaleResult) => void;
}

/**
 * Envoi de la vente et des demandes d'accord. Le brouillon n'est jamais effacé par un échec ;
 * une erreur qui n'est pas prévue par le contrat est relancée au rendu (fail-fast).
 */
export function useSaleSubmit({ shopId, setup, draft, checks, update, onRecorded }: Options) {
  const { sales } = useGateways();
  const [submitting, setSubmitting] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [approvals, setApprovals] = useState<Record<string, "sending" | "pending">>({});
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const fail = (error: unknown) => {
    if (error instanceof ApiError && error.code === "PRICE_BELOW_MINIMUM") {
      const details = priceBelowMinimum(error);
      update({
        serverMinimums: { ...draft.serverMinimums, [details.article_id]: details.min_price },
      });
      setMessage(BELOW_MINIMUM);
      return;
    }
    try {
      setMessage(saleErrorMessage(error, draft.lines, setup.location.name));
    } catch (unexpected) {
      setFatal(unexpected);
    }
  };

  const submit = async () => {
    if (submitting) return;
    setShowErrors(true);
    if (checks.blocking) {
      setMessage(FIX_FIELDS);
      return;
    }
    setMessage(null);
    setSubmitting(true);
    try {
      const command = buildCommand(draft, setup.location.id, checks.total);
      const sale = await sales.recordSale(shopId, command);
      const remembered = draft.payment === CREDIT_CHOICE ? draft.depositMode : draft.payment;
      if (remembered !== null && (draft.payment !== CREDIT_CHOICE || command.payments.length > 0)) {
        writeLastPaymentMode(shopId, remembered);
      }
      onRecorded(sale);
    } catch (error) {
      fail(error);
    } finally {
      setSubmitting(false);
    }
  };

  const requestApproval = async () => {
    const lines = checks.needsApproval.filter((line) => approvals[approvalKey(line)] === undefined);
    setMessage(null);
    for (const line of lines) {
      const key = approvalKey(line);
      if (line.unitPrice === null) throw new Error("Demande d'accord sans prix");
      setApprovals((current) => ({ ...current, [key]: "sending" }));
      try {
        await sales.requestPriceApproval(shopId, {
          id: uuidV7(),
          location_id: setup.location.id,
          article_id: line.article.id,
          requested_price: line.unitPrice,
        });
        setApprovals((current) => ({ ...current, [key]: "pending" }));
      } catch (error) {
        setApprovals((current) =>
          Object.fromEntries(Object.entries(current).filter(([known]) => known !== key)),
        );
        if (error instanceof NetworkError) setMessage(OFFLINE_MESSAGE);
        else setFatal(error);
        return;
      }
    }
  };

  const keys = checks.needsApproval.map(approvalKey);
  const approval =
    keys.length > 0 && keys.every((key) => approvals[key] === "pending")
      ? ("pending" as const)
      : keys.some((key) => approvals[key] === "sending")
        ? ("sending" as const)
        : ("none" as const);

  return { submit, requestApproval, submitting, showErrors, message, approval };
}
