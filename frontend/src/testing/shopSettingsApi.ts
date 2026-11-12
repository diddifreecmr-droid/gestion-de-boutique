/**
 * Faux serveur des Réglages de la boutique (tests seulement) : réponses typées par le contrat
 * généré. Boutique « Motos Garoua » : Garoua (point de vente), Ngaoundéré (entrepôt).
 */
import type {
  ShopLocation,
  ShopMember,
  ShopPaymentMode,
  ShopSettings,
} from "../core/gateways/shopAdminContract";
import { profileBody } from "./catalog";
import { json, meBody, ROUTES, SHOP_A, tokenBody, type Reply } from "./fakeApi";

export const OWNER_ID = "01890a5d-ac96-774b-bcce-b302099a8000";
export const SELLER_ID = "01890a5d-ac96-774b-bcce-b302099a8002";
export const API = `/api/v1/shops/${SHOP_A}`;
export const route = (method: string, path: string) => `${method} ${API}${path}`;
export const SETTINGS_PATH = `/s/${SHOP_A}/reglages`;
export const viewPath = (view: string) => `${SETTINGS_PATH}?vue=${view}`;

/** Charge à l'avance l'écran chargé à la demande (délai des `findBy` sous couverture). */
export async function preloadSettings(): Promise<void> {
  await import("../features/shopSettings/ShopSettingsRoute");
}

export function location(overrides: Partial<ShopLocation> = {}): ShopLocation {
  return {
    id: "loc-garoua",
    name: "Garoua",
    kind: "store",
    is_point_of_sale: true,
    city: "Garoua",
    display_order: 1,
    active: true,
    version: 1,
    ...overrides,
  };
}

export const LOCATIONS: ShopLocation[] = [
  location(),
  location({
    id: "loc-ngaoundere",
    name: "Ngaoundéré",
    kind: "warehouse",
    is_point_of_sale: false,
    city: "Ngaoundéré",
    display_order: 2,
  }),
];

export function member(overrides: Partial<ShopMember> = {}): ShopMember {
  return {
    user_id: SELLER_ID,
    name: "Moussa Hamadou",
    phone: "+237677000002",
    role: "seller",
    default_location_id: "loc-garoua",
    active: true,
    locked: false,
    must_change_pin: false,
    version: 1,
    ...overrides,
  };
}

export const MEMBERS: ShopMember[] = [
  member({
    user_id: OWNER_ID,
    name: "Awa Bello",
    phone: "+237677001122",
    role: "owner",
    default_location_id: null,
  }),
  member(),
];

export function mode(overrides: Partial<ShopPaymentMode> = {}): ShopPaymentMode {
  return {
    id: "mode-cash",
    name: "Espèces",
    reference_required: false,
    active: true,
    display_order: 1,
    version: 1,
    ...overrides,
  };
}

export const MODES: ShopPaymentMode[] = [
  mode(),
  mode({ id: "mode-om", name: "Orange Money", reference_required: true, display_order: 2 }),
];

export function settings(overrides: Partial<ShopSettings> = {}): ShopSettings {
  return {
    version: 3,
    receipt_format: "80mm",
    print_profile: "thermal-80",
    paper_width_mm: 80,
    printable_width_mm: 72,
    margin_mm: 4,
    font_size_pt: 9,
    show_logo: false,
    footer_message: null,
    copies: 1,
    low_stock_threshold: "2.0",
    min_price_enabled: true,
    min_price_requires_approval: false,
    exchange_days: null,
    truck_silent_hours: null,
    transfer_in_transit_days: 7,
    reception_location_id: "loc-garoua",
    header: {
      name: "Motos Garoua",
      city: "Garoua",
      phone: "+237699000000",
      address: null,
      niu: null,
      rccm: null,
    },
    ...overrides,
  };
}

/** Profil « Motos et camions » avec ses quatre rôles (libellés du profil). */
export function profileWithRoles() {
  return {
    ...profileBody("owner"),
    roles: [
      { code: "owner", label: "Propriétaire" },
      { code: "seller", label: "Vendeur" },
      { code: "accountant", label: "Comptable" },
      { code: "driver", label: "Chauffeur" },
    ],
  };
}

export type ShopRoleName = "owner" | "seller" | "accountant" | "driver";

/** Session ouverte pour `role` et lectures des Réglages. */
export function settingsRoutes(role: ShopRoleName = "owner"): Record<string, Reply | Reply[]> {
  const me = meBody({
    user_id: role === "owner" ? OWNER_ID : SELLER_ID,
    shops: [{ shop_id: SHOP_A, shop_name: "Motos Garoua", role }],
  });
  return {
    [ROUTES.refresh]: json(200, tokenBody("t1")),
    [ROUTES.me]: json(200, me),
    [route("GET", "/profile")]: json(200, profileWithRoles()),
    [route("GET", "/members")]: json(200, MEMBERS),
    [route("GET", "/locations")]: json(200, { items: LOCATIONS, read_only: role !== "owner" }),
    [route("GET", "/payment-modes")]: json(200, MODES),
    [route("GET", "/settings")]: json(200, settings()),
  };
}
