/**
 * Référentiels de l'écran Membres : rôles proposés par le profil de la boutique (libellés
 * « Vendeur » ou « Employé »), points de vente actifs (lieu habituel d'un vendeur, MEM-01).
 */
import type {
  ShopAdminGateway,
  ShopLocation,
  ShopMember,
  ShopRole,
} from "../../../core/gateways/shopAdminContract";
import { parseRole } from "../../../core/auth/me";

export interface RoleChoice {
  value: ShopRole;
  label: string;
}

export interface MemberRefs {
  members: ShopMember[];
  roles: RoleChoice[];
  locations: ShopLocation[];
}

export async function loadMemberRefs(
  gateway: ShopAdminGateway,
  shopId: string,
): Promise<MemberRefs> {
  const [members, profile, locations] = await Promise.all([
    gateway.members(shopId),
    gateway.profile(shopId),
    gateway.locations(shopId),
  ]);
  const roles = profile.roles.map((role) => ({ value: parseRole(role.code), label: role.label }));
  if (roles.length === 0) throw new Error("Profil de boutique sans aucun rôle (GET /profile)");
  return { members, roles, locations };
}

export function roleLabel(refs: MemberRefs, role: string): string {
  const found = refs.roles.find((choice) => choice.value === role);
  if (found === undefined) throw new Error(`Rôle « ${role} » absent du profil de la boutique`);
  return found.label;
}

/** Lieux où un vendeur peut avoir son lieu habituel : points de vente actifs. */
export function salePoints(refs: MemberRefs): ShopLocation[] {
  return refs.locations.filter((location) => location.active && location.is_point_of_sale);
}

export function locationName(refs: MemberRefs, id: string | null): string | null {
  if (id === null) return null;
  return refs.locations.find((location) => location.id === id)?.name ?? null;
}
