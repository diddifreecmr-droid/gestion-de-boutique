import { useState } from "react";
import { ApiError } from "../../core/api/errors";
import type { SaleLocation } from "../../core/gateways/catalogContract";
import { useGateways } from "../../core/gateways/gateways";
import { priceBelowMinimum, type PriceRequestProblem } from "../../core/gateways/saleErrors";
import type { PriceRequest, SaleResult } from "../../core/gateways/salesContract";
import { asError } from "./asError";
import { buildCommand } from "./buildCommand";
import { CREDIT_CHOICE, type SaleDraft } from "./draft";
import { writeLastPaymentMode } from "./lastPaymentMode";
import type { ApprovalView } from "./priceRequests/approvalView";
import { problemMessage } from "./priceRequests/priceRequestText";
import type { SaleChecks } from "./saleChecks";
import { saleErrorMessage } from "./saleErrorMessage";

export const FIX_FIELDS = "La vente n'est pas enregistrée : corrigez les champs signalés.";
export const BELOW_MINIMUM = "Prix inférieur au minimum : validation du propriétaire nécessaire.";

/** Ce que l'envoi lit de la demande d'accord (`usePriceApproval`). */
export interface ApprovalLink {
  view: ApprovalView;
  request: PriceRequest | null;
  settle: (problem: PriceRequestProblem) => void;
}

interface Options {
  shopId: string;
  location: SaleLocation;
  draft: SaleDraft;
  checks: SaleChecks;
  approval: ApprovalLink;
  update: (patch: Partial<SaleDraft>) => void;
  onRecorded: (sale: SaleResult) => void;
}

/**
 * Envoi de la vente, avec le `price_request_id` d'un accord reçu. Le brouillon n'est jamais
 * effacé par un échec ; une erreur hors contrat est relancée au rendu (fail-fast).
 */
export function useSaleSubmit(options: Options) {
  const { shopId, location, draft, checks, approval, update, onRecorded } = options;
  const { sales } = useGateways();
  const [submitting, setSubmitting] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [fatal, setFatal] = useState<unknown>(null);
  if (fatal !== null) throw asError(fatal);

  const fail = (error: unknown) => {
    if (error instanceof ApiError && error.code === "PRICE_BELOW_MINIMUM") {
      const details = priceBelowMinimum(error);
      update({
        serverMinimums: { ...draft.serverMinimums, [details.article_id]: details.min_price },
        approvalRequired: true,
      });
      if (details.price_request === null) setMessage(BELOW_MINIMUM);
      else {
        setMessage(problemMessage(details.price_request, approval.request));
        approval.settle(details.price_request);
      }
      return;
    }
    try {
      setMessage(saleErrorMessage(error, draft.lines, location.name));
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
      const accepted = approval.view.kind === "accepted" ? approval.view.requestId : null;
      const command = buildCommand(draft, location.id, checks.total, new Date(), accepted);
      const sale = await sales.recordSale(shopId, command, new Date());
      const remembered = draft.payment === CREDIT_CHOICE ? draft.depositMode : draft.payment;
      if (
        remembered !== null &&
        (draft.payment !== CREDIT_CHOICE || (command.payments ?? []).length > 0)
      ) {
        writeLastPaymentMode(shopId, remembered);
      }
      onRecorded(sale);
    } catch (error) {
      fail(error);
    } finally {
      setSubmitting(false);
    }
  };

  return { submit, submitting, showErrors, message };
}
