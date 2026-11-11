/**
 * Calculs et contrôles de l'écran (CDC UC-VEN-01/02/03, RG-T20, H20). Le serveur reste
 * juge ; ces contrôles évitent un aller-retour et disent tout de suite quoi corriger.
 */
import type { Role } from "../../core/auth/me";
import { formatMoney } from "../../shared/format";
import { CREDIT_CHOICE, minimumOf, type LineDraft, type SaleDraft } from "./draft";
import { normalizePhone } from "./phone";

export interface LineIssues {
  price?: string;
  /** Prix sous le minimum (vu par un vendeur) : le minimum, pour l'avertissement. */
  belowMinimum?: number;
  /** Vrai si la boutique exige l'accord du propriétaire pour ce prix (sinon simple avertissement). */
  approvalRequired?: boolean;
  chassis: (string | undefined)[];
}

export interface SaleChecks {
  total: number;
  /** Montant payé aujourd'hui (comptant : tout ; crédit : l'acompte). */
  paid: number;
  remaining: number;
  lines: Record<string, LineIssues>;
  payment?: string;
  split?: string;
  cashGiven?: string;
  customer?: string;
  customerName?: string;
  customerPhone?: string;
  deposit?: string;
  depositMode?: string;
  /** Monnaie à rendre, si un montant remis est saisi. */
  change: number | null;
  /** Lignes que le vendeur ne peut pas valider seul. */
  needsApproval: LineDraft[];
  /** Erreurs bloquantes (hors accord du propriétaire). */
  blocking: boolean;
}

export function lineTotal(line: LineDraft): number {
  return line.quantity * (line.unitPrice ?? 0);
}

export function splitSum(split: Record<string, number | null>): number {
  return Object.values(split).reduce<number>((sum, amount) => sum + (amount ?? 0), 0);
}

function checkLines(
  draft: SaleDraft,
  role: Role,
  requiresApproval: boolean,
  checks: SaleChecks,
): void {
  const seen = new Set<string>();
  draft.lines.forEach((line) => {
    const issues: LineIssues = { chassis: [] };
    const minimum = minimumOf(draft, line);
    if (line.unitPrice === null) issues.price = "Le prix est vide";
    else if (line.unitPrice < 1) issues.price = "Le prix doit être supérieur à 0";
    else if (role !== "owner" && minimum !== null && line.unitPrice < minimum) {
      issues.belowMinimum = minimum;
      if (requiresApproval) {
        issues.approvalRequired = true;
        checks.needsApproval.push(line);
      }
    }
    issues.chassis = line.units.map((unit) => {
      const chassis = unit.chassis.trim().toUpperCase();
      if (chassis === "") return undefined;
      if (seen.has(chassis)) return "Ce numéro de châssis est déjà saisi dans cette vente";
      seen.add(chassis);
      return undefined;
    });
    checks.lines[line.key] = issues;
  });
}

function checkCash(draft: SaleDraft, checks: SaleChecks): void {
  if (draft.split !== null) {
    const sum = splitSum(draft.split);
    if (sum > checks.total) {
      checks.split = `Le total payé (${formatMoney(sum)}) dépasse le montant de la vente (${formatMoney(checks.total)})`;
    } else if (sum < checks.total) {
      checks.split = `Il manque ${formatMoney(checks.total - sum)} : complétez ou choisissez « À crédit »`;
    }
  }
  checks.paid = checks.total;
  if (draft.split === null && draft.cashGiven !== null) {
    if (draft.cashGiven < checks.total) {
      checks.cashGiven = "Le montant remis est inférieur au total";
    } else checks.change = draft.cashGiven - checks.total;
  }
}

function checkCredit(draft: SaleDraft, checks: SaleChecks): void {
  const { customer } = draft;
  if (customer.mode === "none") {
    checks.customer = "Client obligatoire pour une vente à crédit (nom et téléphone)";
  }
  if (customer.mode === "new") {
    if (customer.name.trim() === "") checks.customerName = "Le nom est vide";
    if (normalizePhone(customer.phone) === null) {
      checks.customerPhone = "Le téléphone doit avoir 9 chiffres";
    }
  }
  const deposit = draft.deposit ?? 0;
  if (deposit > checks.total) {
    checks.deposit = `L'acompte dépasse le montant de la vente (${formatMoney(checks.total)})`;
  } else if (deposit > 0 && draft.depositMode === null) {
    checks.depositMode = "Choisissez le mode de l'acompte";
  }
  checks.paid = Math.min(deposit, checks.total);
}

/** Le client facultatif d'une vente comptant : s'il est commencé, il doit être complet. */
function checkOptionalCustomer(draft: SaleDraft, checks: SaleChecks): void {
  const { customer } = draft;
  if (customer.mode !== "new") return;
  if (customer.name.trim() === "") checks.customerName = "Le nom est vide";
  if (normalizePhone(customer.phone) === null) {
    checks.customerPhone = "Le téléphone doit avoir 9 chiffres";
  }
}

/**
 * `requiresApproval` : réglage « Accord du propriétaire sous le prix minimum » (faux par défaut,
 * décision client) — faux, un prix sous le minimum n'est qu'un avertissement non bloquant.
 */
export function checkSale(draft: SaleDraft, role: Role, requiresApproval: boolean): SaleChecks {
  const checks: SaleChecks = {
    total: draft.lines.reduce((sum, line) => sum + lineTotal(line), 0),
    paid: 0,
    remaining: 0,
    lines: {},
    change: null,
    needsApproval: [],
    blocking: false,
  };
  checkLines(draft, role, requiresApproval, checks);
  if (draft.payment === null) checks.payment = "Choisissez un mode de paiement";
  else if (draft.payment === CREDIT_CHOICE) checkCredit(draft, checks);
  else {
    checkCash(draft, checks);
    checkOptionalCustomer(draft, checks);
  }
  checks.remaining = checks.total - checks.paid;
  const lineBlocking = Object.values(checks.lines).some(
    (issues) => issues.price !== undefined || issues.chassis.some((error) => error !== undefined),
  );
  checks.blocking =
    draft.lines.length === 0 ||
    lineBlocking ||
    [
      checks.payment,
      checks.split,
      checks.cashGiven,
      checks.customer,
      checks.customerName,
      checks.customerPhone,
      checks.deposit,
      checks.depositMode,
    ].some((error) => error !== undefined);
  return checks;
}
