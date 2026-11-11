/**
 * Référentiels des écrans Créances : modes de paiement et — pour le propriétaire seulement
 * (`MEMBER_MANAGE`) — les membres (noms des vendeurs, choix du vendeur responsable).
 */
import type {
  Member,
  PaymentMode,
  ReceivablesGateway,
} from "../../core/gateways/receivablesContract";
import type { ReceivableRole } from "./receivablesNav";

export interface References {
  modes: readonly PaymentMode[];
  /** Membres (propriétaire) ; vide pour le vendeur. */
  members: readonly Member[];
  me: { userId: string; name: string; role: ReceivableRole };
}

export async function loadReferences(
  gateway: ReceivablesGateway,
  shopId: string,
  me: References["me"],
): Promise<References> {
  const [modes, members] = await Promise.all([
    gateway.paymentModes(shopId),
    me.role === "owner" ? gateway.members(shopId) : Promise.resolve([]),
  ]);
  return {
    modes: [...modes].sort((a, b) => a.display_order - b.display_order),
    members,
    me,
  };
}

/** Modes proposés à la saisie : les actifs seulement. */
export const activeModes = (refs: References) => refs.modes.filter((mode) => mode.active);

/** Nom d'un mode ; un mode inconnu est une incohérence de données (fail-fast). */
export function modeName(refs: References, id: string): string {
  const found = refs.modes.find((mode) => mode.id === id);
  if (found === undefined) throw new Error(`Mode de paiement inconnu : « ${id} »`);
  return found.name;
}

/** Vendeurs proposés comme responsables (propriétaire) : membres vendeurs actifs. */
export const sellers = (refs: References) =>
  refs.members.filter((member) => member.role === "seller" && member.active);

/** Nom d'un membre : « vous », son nom (propriétaire), sinon « un autre membre ». */
export function memberName(refs: References, userId: string | null): string {
  if (userId === null) return "Aucun";
  if (userId === refs.me.userId) return "vous";
  return refs.members.find((member) => member.user_id === userId)?.name ?? "un autre membre";
}
