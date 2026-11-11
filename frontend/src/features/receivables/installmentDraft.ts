/** Saisie d'un versement (UC-CRE-03) : contrôles avant envoi et corps de la requête. */
import type { InstallmentCreate, PaymentMode } from "../../core/gateways/receivablesContract";
import { formatMoney } from "../../shared/format";
import { dateProblem } from "../expenses/businessDay";

export interface InstallmentDraft {
  amount: number | null;
  modeId: string | null;
  paidOn: string;
  reference: string;
}

export interface InstallmentProblems {
  amount?: string;
  mode?: string;
  date?: string;
  reference?: string;
}

export function emptyInstallment(modes: readonly PaymentMode[], today: string): InstallmentDraft {
  return { amount: null, modeId: modes[0]?.id ?? null, paidOn: today, reference: "" };
}

/** Reste après ce versement, ou `null` tant que le montant n'est pas saisi. */
export function remainingAfter(remaining: number, amount: number | null): number | null {
  if (amount === null || amount <= 0 || amount > remaining) return null;
  return remaining - amount;
}

export function installmentProblems(
  draft: InstallmentDraft,
  context: { remaining: number; modes: readonly PaymentMode[]; today: string; isOwner: boolean },
): InstallmentProblems {
  const problems: InstallmentProblems = {};
  if (draft.amount === null || draft.amount <= 0) problems.amount = "Le montant est vide";
  else if (draft.amount > context.remaining) {
    problems.amount = `Le versement dépasse le reste à payer : il reste ${formatMoney(context.remaining)}.`;
  }
  const mode = context.modes.find((item) => item.id === draft.modeId);
  if (mode === undefined) problems.mode = "Choisissez le mode de paiement";
  else if (mode.reference_required && draft.reference.trim() === "") {
    problems.reference = `La référence est obligatoire pour ${mode.name}`;
  }
  const date = dateProblem(draft.paidOn, context.today, context.isOwner);
  if (date !== undefined) problems.date = date;
  return problems;
}

export function installmentBody(draft: InstallmentDraft, id: string): InstallmentCreate {
  if (draft.amount === null || draft.modeId === null) {
    throw new Error("Versement incomplet envoyé (contrôles contournés)");
  }
  const reference = draft.reference.trim();
  return {
    id,
    amount: draft.amount,
    mode_id: draft.modeId,
    paid_on: draft.paidOn,
    reference: reference === "" ? null : reference,
  };
}
