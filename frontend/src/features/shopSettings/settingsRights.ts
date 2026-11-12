import type { Role } from "../../core/auth/me";

/**
 * Rôles qui ouvrent les Réglages de la boutique : CDC § 4.2 « Gérer les utilisateurs et les
 * réglages de la boutique » = propriétaire seul (backend `MEMBER_MANAGE`, `SETTINGS_MANAGE`,
 * `LOCATION_MANAGE`). Le comptable lit les lieux par l'API mais n'a pas d'entrée « Réglages ».
 */
export const SETTINGS_ROLES: readonly Role[] = ["owner"];
