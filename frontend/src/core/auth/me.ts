/** Identité de l'utilisateur connecté, lue depuis `GET /me` et vérifiée (fail-fast). */
import type { MeResponse } from "../api/types";

/** Codes stables des rôles de boutique (backend `Role`, CDC § 4.1). */
export const ROLES = ["owner", "seller", "accountant", "driver"] as const;
export type Role = (typeof ROLES)[number];

export interface ShopMembership {
  shopId: string;
  shopName: string;
  role: Role;
}

export interface Me {
  userId: string;
  name: string;
  phone: string;
  isPlatformAdmin: boolean;
  mustChangePin: boolean;
  shops: readonly ShopMembership[];
}

export function parseRole(value: string): Role {
  const role = ROLES.find((known) => known === value);
  if (role === undefined) {
    throw new Error(`Rôle inconnu reçu de l'API : « ${value} » (attendu ${ROLES.join(", ")})`);
  }
  return role;
}

export function parseMe(response: MeResponse): Me {
  return {
    userId: response.user_id,
    name: response.name,
    phone: response.phone,
    isPlatformAdmin: response.is_platform_admin,
    mustChangePin: response.must_change_pin,
    shops: response.shops.map((shop) => ({
      shopId: shop.shop_id,
      shopName: shop.shop_name,
      role: parseRole(shop.role),
    })),
  };
}
