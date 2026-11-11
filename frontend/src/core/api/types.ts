/** Alias lisibles des schémas générés (schema.gen.ts) : aucun type de l'API n'est réécrit. */
import type { components } from "./schema.gen";

type Schemas = components["schemas"];

export type LoginRequest = Schemas["LoginRequest"];
export type TokenResponse = Schemas["TokenResponse"];
export type ChangePinRequest = Schemas["ChangePinRequest"];
export type MeResponse = Schemas["MeResponse"];
export type ShopMembershipResponse = Schemas["ShopMembershipResponse"];
