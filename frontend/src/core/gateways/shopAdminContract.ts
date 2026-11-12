/**
 * Passerelle des « Réglages de la boutique » (specs § 6.3 « Boutique », UC-SOC-04 à 06) :
 * membres, lieux, modes de paiement, réglages. L'écran dépend de cette interface, jamais de
 * `fetch`. Tous les types viennent du contrat **généré** (schema.gen.ts).
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

export type ShopRole = Schemas["Role"];
export type ShopMember = Schemas["MemberResponse"];
export type MemberCreate = Schemas["MemberCreateRequest"];
export type MemberCreated = Schemas["MemberCreatedResponse"];
export type MemberPatch = Schemas["MemberPatch"];
export type ShopLocation = Schemas["LocationResponse"];
export type LocationKind = Schemas["LocationKind"];
export type LocationCreate = Schemas["LocationCreateRequest"];
export type LocationPatch = Schemas["LocationPatch"];
export type ShopPaymentMode = Schemas["PaymentModeResponse"];
export type PaymentModeCreate = Schemas["PaymentModeCreateRequest"];
export type PaymentModePatch = Schemas["PaymentModePatch"];
export type ShopSettings = Schemas["SettingsResponse"];
export type SettingsPatch = Schemas["SettingsPatch"];
export type ReceiptFormat = Schemas["ReceiptFormat"];
export type ShopProfileInfo = Schemas["ProfileResponse"];

export interface ShopAdminGateway {
  /** Rôles proposés par le profil de la boutique et leurs libellés (« Vendeur », « Employé »). */
  profile(shopId: string): Promise<ShopProfileInfo>;
  members(shopId: string): Promise<ShopMember[]>;
  /** Code provisoire renvoyé **une seule fois** (null si le compte existait déjà). */
  addMember(shopId: string, body: MemberCreate): Promise<MemberCreated>;
  updateMember(shopId: string, userId: string, patch: MemberPatch): Promise<ShopMember>;
  resetPin(shopId: string, userId: string): Promise<string>;
  revokeDevices(shopId: string, userId: string): Promise<number>;
  unlock(shopId: string, userId: string): Promise<void>;
  locations(shopId: string): Promise<ShopLocation[]>;
  createLocation(shopId: string, body: LocationCreate): Promise<ShopLocation>;
  updateLocation(shopId: string, locationId: string, patch: LocationPatch): Promise<ShopLocation>;
  paymentModes(shopId: string): Promise<ShopPaymentMode[]>;
  createPaymentMode(shopId: string, body: PaymentModeCreate): Promise<ShopPaymentMode>;
  updatePaymentMode(
    shopId: string,
    modeId: string,
    patch: PaymentModePatch,
  ): Promise<ShopPaymentMode>;
  settings(shopId: string): Promise<ShopSettings>;
  updateSettings(shopId: string, patch: SettingsPatch): Promise<ShopSettings>;
}
