/**
 * `GET /profile` tel que le sert le vrai serveur : **par acteur** (menu et libellé de son rôle).
 * Le faux serveur de `renderApp` passe chaque réponse de profil par `servedAs`, avec le rôle
 * que `GET /me` donne pour la boutique. Tests seulement.
 */
import type { components } from "../core/api/schema.gen";
import type { Role } from "../core/auth/me";
import { AVAILABLE_OPTIONAL_MODULES, ALWAYS_ON } from "../core/profile/modules";
import { profileBody } from "./catalog";
import { json, ROUTES, type Reply } from "./fakeApi";
import {
  isServedCode,
  SERVED_MENUS,
  SERVED_ROLES,
  visibleMenu,
  type ServedProfileCode,
} from "./profileMenus";

type ProfileResponse = components["schemas"]["ProfileResponse"];
type Field = components["schemas"]["FieldResponse"];
type Routes = Record<string, Reply | Reply[]>;

/** La réponse vue par `role` : rôles du profil, libellé et menu de ce rôle (modules actifs). */
export function servedAs<T extends ProfileResponse>(body: T, role: Role): T {
  const code = body.profile_code;
  if (!isServedCode(code)) throw new Error(`Faux serveur : profil « ${code} » inconnu`);
  const labels = SERVED_ROLES[code];
  const menu = SERVED_MENUS[code][role];
  const label = labels[role];
  if (menu === undefined || label === undefined) {
    throw new Error(`Faux serveur : le profil « ${code} » n'a pas de rôle « ${role} »`);
  }
  return {
    ...body,
    roles: Object.entries(labels).map(([roleCode, roleLabel]) => ({
      code: roleCode,
      label: roleLabel,
    })),
    role,
    role_label: label,
    menu: visibleMenu(menu, body.enabled_modules),
  };
}

const field = (code: string, label: string, kind = "text", required = false): Field => ({
  code,
  label,
  kind,
  required,
  unique: code === "reference",
  choices: code === "unit" ? ["METER", "PIECE"] : [],
});

const APPAREL_FIELDS = {
  profile_label: "Prêt-à-porter",
  article_fields: [
    field("name", "Nom", "text", true),
    field("reference", "Référence"),
    field("category", "Catégorie"),
    field("type", "Type"),
    field("brand", "Marque"),
  ],
  sale_fields: [field("size", "Taille"), field("color", "Couleur")],
  stock_units: ["PIECE"],
};

const TEXTILE_FIELDS = {
  profile_label: "Textile",
  article_fields: [
    field("name", "Nom", "text", true),
    field("reference", "Référence"),
    field("type", "Type"),
    field("unit", "Unité", "choice", true),
    field("sold_by_piece", "Vente à la pièce", "boolean"),
    field("piece_length_m", "Longueur de la pièce (m)", "decimal"),
  ],
  sale_fields: [field("length_m", "Longueur (m)", "decimal")],
  stock_units: ["METER", "PIECE"],
};

/** Modules de départ d'un profil : Motos tous (disponibles), les autres de même ici. */
const OPENING = [...ALWAYS_ON, ...AVAILABLE_OPTIONAL_MODULES];

/** Profil complet servi pour `role` d'une boutique `code`. */
export function servedProfile(
  code: ServedProfileCode,
  role: Role,
  modules: readonly string[] = OPENING,
): ProfileResponse {
  const base = { ...profileBody("owner"), enabled_modules: [...modules] };
  const extra = code === "apparel" ? APPAREL_FIELDS : code === "textile" ? TEXTILE_FIELDS : {};
  return servedAs({ ...base, profile_code: code, ...extra }, role);
}

async function roleFor(routes: Routes, shopId: string): Promise<Role | null> {
  const entry = Reflect.get(routes, ROUTES.me) as Reply | Reply[] | undefined;
  const list = entry === undefined ? [] : Array.isArray(entry) ? entry : [entry];
  for (const reply of list) {
    if (!(reply instanceof Response) || !reply.ok) continue;
    const me = (await reply.clone().json()) as components["schemas"]["MeResponse"];
    const shop = me.shops.find((one) => one.shop_id === shopId);
    if (shop !== undefined) return shop.role as Role;
  }
  return null;
}

/** Réponse de profil de `shopId` vue par l'acteur de `GET /me` (sinon telle quelle). */
export function perActor(routes: Routes, shopId: string, reply: Reply): Reply {
  if (reply instanceof Error || reply instanceof DOMException) return reply;
  return async (call) => {
    const response = typeof reply === "function" ? await reply(call) : reply.clone();
    if (!response.ok) return response;
    const body = (await response.json()) as ProfileResponse;
    const role = (await roleFor(routes, shopId)) ?? (body.role as Role | null);
    return json(response.status, role === null ? body : servedAs(body, role));
  };
}
