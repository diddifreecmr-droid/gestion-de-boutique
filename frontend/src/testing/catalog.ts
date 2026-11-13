/** Données et routes du faux serveur pour les écrans du catalogue (tests seulement). */
import type { components } from "../core/api/schema.gen";
import { ALL_MODULES } from "../core/profile/modules";
import type { ArticleResponse } from "../core/gateways/catalogAdminContract";
import { json, meBody, ROUTES, SHOP_A, tokenBody, type Reply } from "./fakeApi";

type Role = "owner" | "seller" | "accountant" | "driver";
type Routes = Record<string, Reply | Reply[]>;

export const HAOJUE_ID = "01890a5d-ac96-774b-bcce-b302099a8101";
export const YAMAHA_ID = "01890a5d-ac96-774b-bcce-b302099a8102";
export const API = `/api/v1/shops/${SHOP_A}`;

export function profileBody(role: Role, minPriceEnabled = true) {
  const profile: components["schemas"]["ProfileResponse"] = {
    shop_id: SHOP_A,
    profile_code: "motos",
    profile_version: 1,
    profile_label: "Motos et camions",
    enabled_modules: [...ALL_MODULES],
    roles: [],
    role,
    role_label: null,
    menu: [],
    article_fields: [
      { code: "brand", label: "Marque", kind: "text", required: true, unique: false, choices: [] },
      { code: "model", label: "Modèle", kind: "text", required: true, unique: false, choices: [] },
      {
        code: "engine_cc",
        label: "Cylindrée (cm³)",
        kind: "integer",
        required: false,
        unique: false,
        choices: [],
      },
      {
        code: "category",
        label: "Catégorie",
        kind: "text",
        required: false,
        unique: false,
        choices: [],
      },
    ],
    sale_fields: [],
    stock_units: ["unit"],
    receipt: {
      format: "80mm",
      print_profile: "thermal-80",
      paper_width_mm: 80,
      printable_width_mm: 72,
      margin_mm: 4,
      font_size_pt: 9,
      show_logo: false,
      copies: 1,
      footer_message: null,
      header: {
        name: "Motos Garoua",
        city: "Garoua",
        phone: "",
        address: null,
        niu: null,
        rccm: null,
      },
    },
    min_price_enabled: minPriceEnabled,
    min_price_requires_approval: false,
    default_location_id: null,
    entitlements: { offline_capture: false },
  };
  return profile;
}

/** Article tel que l'API l'envoie **au propriétaire** (prix, coûts). */
export function ownerArticle(overrides: Partial<ArticleResponse> = {}): ArticleResponse {
  return {
    id: HAOJUE_ID,
    version: 3,
    status: "active",
    display_name: "Haojue HJ125-8",
    brand: "Haojue",
    model: "HJ125-8",
    reference: null,
    stock_unit: "unit",
    sold_by_piece: false,
    piece_length_m: null,
    attributes: { engine_cc: 125 },
    alert_threshold: null,
    effective_alert_threshold: "2",
    photo_id: null,
    notes: null,
    created_at: "2026-11-02T08:00:00Z",
    base_price: 780000,
    base_price_piece: null,
    min_price: 720000,
    min_price_piece: null,
    min_price_active: true,
    last_cost: 650000,
    wac: null,
    ...overrides,
  };
}

/** Même article vu par le comptable : aucun prix de vente (clés absentes, TR-05). */
export function accountantArticle(overrides: Partial<ArticleResponse> = {}): ArticleResponse {
  const raw: Partial<ArticleResponse> = { ...ownerArticle(), ...overrides };
  delete raw.base_price;
  delete raw.base_price_piece;
  delete raw.min_price;
  delete raw.min_price_piece;
  delete raw.min_price_active;
  delete raw.price_history;
  return raw as ArticleResponse;
}

export function signedIn(role: Role): Routes {
  const me = meBody({ shops: [{ shop_id: SHOP_A, shop_name: "Motos Garoua", role }] });
  return { [ROUTES.refresh]: json(200, tokenBody("t1")), [ROUTES.me]: json(200, me) };
}

export function listUrl(q: string | null = null, status = "active", cursor: string | null = null) {
  const params = new URLSearchParams();
  if (q !== null) params.append("q", q);
  params.append("status", status);
  if (cursor !== null) params.append("cursor", cursor);
  params.append("limit", "20");
  return `GET ${API}/articles?${params.toString()}`;
}

/** Une réponse par préfixe tapé (« h », « ha », « hao »…) : la recherche part à chaque lettre. */
export function typedSearch(text: string, reply: Reply, status = "active"): Routes {
  const routes: Routes = {};
  for (let end = 1; end <= text.length; end += 1) {
    routes[listUrl(text.slice(0, end), status)] = reply;
  }
  return routes;
}

export function catalogRoutes(role: Role, extra: Routes = {}): Routes {
  return {
    ...signedIn(role),
    [`GET ${API}/profile`]: json(200, profileBody(role)),
    ...extra,
  };
}
