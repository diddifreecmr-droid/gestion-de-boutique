import type { Role } from "../../core/auth/me";

/** Rôles qui enregistrent une vente (UC-VEN-01 / 02) : le vendeur et le propriétaire. */
export const SALE_ROLES: readonly Role[] = ["owner", "seller"];
