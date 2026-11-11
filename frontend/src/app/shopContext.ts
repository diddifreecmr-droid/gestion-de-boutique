import { useOutletContext } from "react-router";
import type { Role } from "../core/auth/me";
import type { ShopProfile } from "../core/profile/types";

/** Boutique active, transmise par la coquille aux pages (via l'Outlet). */
export interface ActiveShop {
  shopId: string;
  shopName: string;
  role: Role;
  profile: ShopProfile;
}

export function useActiveShop(): ActiveShop {
  return useOutletContext<ActiveShop>();
}
