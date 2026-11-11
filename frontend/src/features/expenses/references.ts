/**
 * Référentiels des écrans Dépenses : catégories, modes de paiement, lieux et — pour le
 * propriétaire seulement (`MEMBER_MANAGE`) — les noms des membres. Une référence inconnue
 * est une incohérence de données : on lève plutôt que d'afficher un identifiant.
 */
import type { Role } from "../../core/auth/me";
import type {
  ExpenseCategory,
  ExpensesGateway,
  Location,
  PaymentMode,
} from "../../core/gateways/expensesContract";

export interface References {
  categories: readonly ExpenseCategory[];
  modes: readonly PaymentMode[];
  locations: readonly Location[];
  /** Noms des membres (propriétaire) ; vide pour le comptable. */
  members: ReadonlyMap<string, string>;
  me: { userId: string; name: string; role: Role };
}

export async function loadReferences(
  gateway: ExpensesGateway,
  shopId: string,
  me: References["me"],
): Promise<References> {
  const [categories, modes, locations, members] = await Promise.all([
    gateway.categories(shopId),
    gateway.paymentModes(shopId),
    gateway.locations(shopId),
    me.role === "owner" ? gateway.members(shopId) : Promise.resolve([]),
  ]);
  const byOrder = <T extends { display_order: number }>(items: readonly T[]): T[] =>
    [...items].sort((a, b) => a.display_order - b.display_order);
  return {
    categories: byOrder(categories),
    modes: byOrder(modes),
    locations: byOrder(locations),
    members: new Map(members.map((member) => [member.user_id, member.name])),
    me,
  };
}

function named(items: readonly { id: string; name: string }[], id: string, kind: string): string {
  const found = items.find((item) => item.id === id);
  if (found === undefined) throw new Error(`${kind} inconnu(e) : « ${id} »`);
  return found.name;
}

export const categoryName = (refs: References, id: string) =>
  named(refs.categories, id, "Catégorie");
export const modeName = (refs: References, id: string) => named(refs.modes, id, "Mode de paiement");
export const locationName = (refs: References, id: string) => named(refs.locations, id, "Lieu");

/** Auteur d'une saisie : son nom pour le propriétaire, « vous » ou « un autre membre » sinon. */
export function authorName(refs: References, userId: string): string {
  if (userId === refs.me.userId) return refs.me.name;
  return refs.members.get(userId) ?? "un autre membre";
}

/**
 * Auteur d'une annulation. Le comptable n'annule que ses dépenses : une annulation qui n'est
 * pas de lui vient forcément du propriétaire (matrice `EXPENSE_CORRECT`).
 */
export function cancellerName(refs: References, userId: string): string {
  if (userId === refs.me.userId) return refs.me.name;
  return refs.members.get(userId) ?? "le propriétaire";
}
