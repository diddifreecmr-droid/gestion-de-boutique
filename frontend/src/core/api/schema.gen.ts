/* Fichier GÉNÉRÉ par `npm run gen:api` depuis backend/openapi.json : ne pas modifier. */
export interface paths {
  "/api/v1/health": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Health */
    get: operations["health_api_v1_health_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/auth/login": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Login */
    post: operations["login_api_v1_auth_login_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/auth/refresh": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Refresh */
    post: operations["refresh_api_v1_auth_refresh_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/auth/logout": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Logout */
    post: operations["logout_api_v1_auth_logout_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/auth/change-pin": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Change Pin */
    post: operations["change_pin_api_v1_auth_change_pin_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/me": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Me */
    get: operations["me_api_v1_me_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/audit": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Journal List */
    get: operations["journal_list_api_v1_shops__shop_id__audit_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/audit/entities/{entity_type}/{entity_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Entity History */
    get: operations["entity_history_api_v1_shops__shop_id__audit_entities__entity_type___entity_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/audit/users/{user_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** User Activity */
    get: operations["user_activity_api_v1_shops__shop_id__audit_users__user_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/alerts": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Alerts */
    get: operations["list_alerts_api_v1_shops__shop_id__alerts_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/alerts/{alert_id}/read": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Mark Alert Read */
    post: operations["mark_alert_read_api_v1_shops__shop_id__alerts__alert_id__read_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/platform/shops": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Shops */
    get: operations["list_shops_api_v1_platform_shops_get"];
    put?: never;
    /** Open Shop */
    post: operations["open_shop_api_v1_platform_shops_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/platform/shops/{shop_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Shop */
    get: operations["get_shop_api_v1_platform_shops__shop_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Administer Shop */
    patch: operations["administer_shop_api_v1_platform_shops__shop_id__patch"];
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/profile": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Profile */
    get: operations["profile_api_v1_shops__shop_id__profile_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/settings": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Settings */
    get: operations["get_settings_api_v1_shops__shop_id__settings_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Patch Settings */
    patch: operations["patch_settings_api_v1_shops__shop_id__settings_patch"];
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/locations": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Locations */
    get: operations["list_locations_api_v1_shops__shop_id__locations_get"];
    put?: never;
    /** Create Location */
    post: operations["create_location_api_v1_shops__shop_id__locations_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/locations/{location_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Patch Location */
    patch: operations["patch_location_api_v1_shops__shop_id__locations__location_id__patch"];
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/payment-modes": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Payment Modes */
    get: operations["list_payment_modes_api_v1_shops__shop_id__payment_modes_get"];
    put?: never;
    /** Create Payment Mode */
    post: operations["create_payment_mode_api_v1_shops__shop_id__payment_modes_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/payment-modes/{mode_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Patch Payment Mode */
    patch: operations["patch_payment_mode_api_v1_shops__shop_id__payment_modes__mode_id__patch"];
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/members": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Members */
    get: operations["list_members_api_v1_shops__shop_id__members_get"];
    put?: never;
    /** Add Member */
    post: operations["add_member_api_v1_shops__shop_id__members_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/members/{user_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Patch Member */
    patch: operations["patch_member_api_v1_shops__shop_id__members__user_id__patch"];
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/members/{user_id}/reset-pin": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Reset Pin */
    post: operations["reset_pin_api_v1_shops__shop_id__members__user_id__reset_pin_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/members/{user_id}/revoke-devices": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Revoke Devices */
    post: operations["revoke_devices_api_v1_shops__shop_id__members__user_id__revoke_devices_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/members/{user_id}/unlock": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Unlock */
    post: operations["unlock_api_v1_shops__shop_id__members__user_id__unlock_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/admin-access": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Admin Access */
    get: operations["admin_access_api_v1_shops__shop_id__admin_access_get"];
    put?: never;
    /** Grant Admin Access */
    post: operations["grant_admin_access_api_v1_shops__shop_id__admin_access_post"];
    /** Revoke Admin Access */
    delete: operations["revoke_admin_access_api_v1_shops__shop_id__admin_access_delete"];
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
}
export type webhooks = Record<string, never>;
export interface components {
  schemas: {
    /** AdminAccessResponse */
    AdminAccessResponse: {
      /** Active */
      active: boolean;
      /** Expires At */
      expires_at: string | null;
    };
    /**
     * AdministerShopRequest
     * @description Champs absents : inchangés. `entitlements[x] = null` retire la surcharge.
     */
    AdministerShopRequest: {
      /** Modules */
      modules?: components["schemas"]["Module"][] | null;
      status?: components["schemas"]["ShopStatus"] | null;
      /** Entitlements */
      entitlements?: {
        [key: string]: boolean | null;
      };
    };
    /** AlertPageResponse */
    AlertPageResponse: {
      /** Items */
      items: components["schemas"]["AlertResponse"][];
      /** Next Cursor */
      next_cursor: string | null;
      /** Unread Count */
      unread_count: number;
    };
    /** AlertResponse */
    AlertResponse: {
      /** Id */
      id: string;
      /** Type */
      type: string;
      entity: components["schemas"]["EntityResponse"];
      /** Message */
      message: string;
      /** Read */
      read: boolean;
      /** Active */
      active: boolean;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
    };
    /**
     * AuditAction
     * @description Les onze actions du CDC § 16.1 (code stable ; libellé français dans `label`).
     * @enum {string}
     */
    AuditAction:
      | "create"
      | "update"
      | "cancel"
      | "validate"
      | "reject"
      | "login"
      | "logout"
      | "print"
      | "import"
      | "configure"
      | "access_denied";
    /** AuditEntryResponse */
    AuditEntryResponse: {
      /** Id */
      id: string;
      /**
       * Captured At
       * Format: date-time
       */
      captured_at: string;
      /**
       * Received At
       * Format: date-time
       */
      received_at: string;
      performer: components["schemas"]["PerformerResponse"];
      /** Action */
      action: string;
      /** Action Label */
      action_label: string;
      /** Module */
      module: string;
      entity: components["schemas"]["EntityResponse"];
      /** Summary */
      summary: string;
      /** Changes */
      changes: components["schemas"]["FieldChangeResponse"][];
      /** Reason */
      reason: string | null;
      /** Sensitive */
      sensitive: boolean;
    };
    /** AuditPageResponse */
    AuditPageResponse: {
      /** Items */
      items: components["schemas"]["AuditEntryResponse"][];
      /** Next Cursor */
      next_cursor: string | null;
    };
    /**
     * ChangePinRequest
     * @description Pour l'administrateur plateforme, ces champs portent le mot de passe.
     */
    ChangePinRequest: {
      /** Current Pin */
      current_pin: string;
      /** New Pin */
      new_pin: string;
      /** New Pin Confirmation */
      new_pin_confirmation: string;
    };
    /**
     * Entitlement
     * @description Code stable d'un droit d'offre (stocké, renvoyé dans `error.details`).
     * @enum {string}
     */
    Entitlement: "offline_capture";
    /** EntityResponse */
    EntityResponse: {
      /** Type */
      type: string;
      /** Id */
      id: string | null;
      /** Number */
      number: string | null;
    };
    /** FieldChangeResponse */
    FieldChangeResponse: {
      /** Field */
      field: string;
      /** Before */
      before: string | number | boolean | null;
      /** After */
      after: string | number | boolean | null;
    };
    /** FieldResponse */
    FieldResponse: {
      /** Code */
      code: string;
      /** Label */
      label: string;
      /** Kind */
      kind: string;
      /** Required */
      required: boolean;
      /** Unique */
      unique: boolean;
      /** Choices */
      choices: string[];
    };
    /** HTTPValidationError */
    HTTPValidationError: {
      /** Detail */
      detail?: components["schemas"]["ValidationError"][];
    };
    /** HealthResponse */
    HealthResponse: {
      /**
       * Status
       * @constant
       */
      status: "ok";
    };
    /** LocationCreateRequest */
    LocationCreateRequest: {
      /** Id */
      id?: string | null;
      /** Name */
      name: string;
      kind: components["schemas"]["LocationKind"];
      /** Is Point Of Sale */
      is_point_of_sale: boolean;
      /** City */
      city?: string | null;
      /**
       * Display Order
       * @default 0
       */
      display_order: number;
    };
    /**
     * LocationKind
     * @enum {string}
     */
    LocationKind: "store" | "warehouse";
    /** LocationListResponse */
    LocationListResponse: {
      /** Items */
      items: components["schemas"]["LocationResponse"][];
      /** Read Only */
      read_only: boolean;
    };
    /** LocationPatch */
    LocationPatch: {
      /** Version */
      version: number;
      /** Name */
      name?: string | null;
      kind?: components["schemas"]["LocationKind"] | null;
      /** Is Point Of Sale */
      is_point_of_sale?: boolean | null;
      /** City */
      city?: string | null;
      /** Display Order */
      display_order?: number | null;
      /** Active */
      active?: boolean | null;
    };
    /** LocationResponse */
    LocationResponse: {
      /** Id */
      id: string;
      /** Name */
      name: string;
      /** Kind */
      kind: string;
      /** Is Point Of Sale */
      is_point_of_sale: boolean;
      /** City */
      city: string | null;
      /** Display Order */
      display_order: number;
      /** Active */
      active: boolean;
      /** Version */
      version: number;
    };
    /**
     * LoginRequest
     * @description Code à 6 chiffres (membre) **ou** mot de passe (administrateur plateforme).
     */
    LoginRequest: {
      /** Phone */
      phone: string;
      /** Pin */
      pin?: string | null;
      /** Password */
      password?: string | null;
      /**
       * Device Label
       * @example Android — Chrome
       */
      device_label: string;
    };
    /** MeResponse */
    MeResponse: {
      /** User Id */
      user_id: string;
      /** Name */
      name: string;
      /** Phone */
      phone: string;
      /** Is Platform Admin */
      is_platform_admin: boolean;
      /** Must Change Pin */
      must_change_pin: boolean;
      /** Shops */
      shops: components["schemas"]["ShopMembershipResponse"][];
    };
    /** MemberCreateRequest */
    MemberCreateRequest: {
      /** Name */
      name: string;
      /** Phone */
      phone: string;
      role: components["schemas"]["Role"];
      /** Default Location Id */
      default_location_id?: string | null;
    };
    /** MemberCreatedResponse */
    MemberCreatedResponse: {
      member: components["schemas"]["MemberResponse"];
      /** Temporary Pin */
      temporary_pin: string | null;
      /** Existing Account */
      existing_account: boolean;
    };
    /** MemberPatch */
    MemberPatch: {
      /** Version */
      version: number;
      role?: components["schemas"]["Role"] | null;
      /** Default Location Id */
      default_location_id?: string | null;
      /** Active */
      active?: boolean | null;
    };
    /** MemberResponse */
    MemberResponse: {
      /** User Id */
      user_id: string;
      /** Name */
      name: string;
      /** Phone */
      phone: string;
      /** Role */
      role: string;
      /** Default Location Id */
      default_location_id: string | null;
      /** Active */
      active: boolean;
      /** Locked */
      locked: boolean;
      /** Must Change Pin */
      must_change_pin: boolean;
      /** Version */
      version: number;
    };
    /** MenuEntryResponse */
    MenuEntryResponse: {
      /** Code */
      code: string;
      /** Label */
      label: string;
      /** Module */
      module: string;
      /** Children */
      children: components["schemas"]["MenuEntryResponse"][];
    };
    /**
     * Module
     * @enum {string}
     */
    Module:
      | "core"
      | "catalog"
      | "purchases"
      | "sales"
      | "receivables"
      | "expenses"
      | "transfers"
      | "transport"
      | "dashboard"
      | "import"
      | "audit";
    /** OpenShopRequest */
    OpenShopRequest: {
      /**
       * Profile Code
       * @example motos
       */
      profile_code: string;
      /** Name */
      name: string;
      /** City */
      city: string;
      /** Phone */
      phone: string;
      /** Address */
      address?: string | null;
      /** Niu */
      niu?: string | null;
      /** Rccm */
      rccm?: string | null;
      owner: components["schemas"]["OwnerRequest"];
      /** Account Name */
      account_name?: string | null;
    };
    /** OpenedShopResponse */
    OpenedShopResponse: {
      shop: components["schemas"]["ShopSummaryResponse"];
      /** Owner Id */
      owner_id: string;
      /** Owner Created */
      owner_created: boolean;
      /** Temporary Pin */
      temporary_pin: string | null;
    };
    /** OwnerRequest */
    OwnerRequest: {
      /** Name */
      name: string;
      /** Phone */
      phone: string;
    };
    /** PaymentModeCreateRequest */
    PaymentModeCreateRequest: {
      /** Id */
      id?: string | null;
      /** Name */
      name: string;
      /**
       * Reference Required
       * @default false
       */
      reference_required: boolean;
      /**
       * Display Order
       * @default 0
       */
      display_order: number;
    };
    /** PaymentModePatch */
    PaymentModePatch: {
      /** Version */
      version: number;
      /** Name */
      name?: string | null;
      /** Reference Required */
      reference_required?: boolean | null;
      /** Active */
      active?: boolean | null;
      /** Display Order */
      display_order?: number | null;
    };
    /** PaymentModeResponse */
    PaymentModeResponse: {
      /** Id */
      id: string;
      /** Name */
      name: string;
      /** Reference Required */
      reference_required: boolean;
      /** Active */
      active: boolean;
      /** Display Order */
      display_order: number;
      /** Version */
      version: number;
    };
    /** PerformerResponse */
    PerformerResponse: {
      /** User Id */
      user_id: string;
      /** Role */
      role: string;
      /** Device Id */
      device_id: string | null;
    };
    /** ProfileResponse */
    ProfileResponse: {
      /** Shop Id */
      shop_id: string;
      /** Profile Code */
      profile_code: string;
      /** Profile Version */
      profile_version: number;
      /** Profile Label */
      profile_label: string;
      /** Enabled Modules */
      enabled_modules: string[];
      /** Roles */
      roles: components["schemas"]["RoleResponse"][];
      /** Role */
      role: string | null;
      /** Role Label */
      role_label: string | null;
      /** Menu */
      menu: components["schemas"]["MenuEntryResponse"][];
      /** Article Fields */
      article_fields: components["schemas"]["FieldResponse"][];
      /** Sale Fields */
      sale_fields: components["schemas"]["FieldResponse"][];
      /** Stock Units */
      stock_units: string[];
      receipt: components["schemas"]["ReceiptResponse"];
      /** Min Price Enabled */
      min_price_enabled: boolean;
      /** Default Location Id */
      default_location_id: string | null;
    };
    /**
     * ReceiptFormat
     * @enum {string}
     */
    ReceiptFormat: "58mm" | "80mm" | "a5" | "a4";
    /** ReceiptResponse */
    ReceiptResponse: {
      /** Format */
      format: string;
      /** Print Profile */
      print_profile: string;
      /** Paper Width Mm */
      paper_width_mm: number;
      /** Printable Width Mm */
      printable_width_mm: number;
      /** Margin Mm */
      margin_mm: number;
      /** Font Size Pt */
      font_size_pt: number;
      /** Show Logo */
      show_logo: boolean;
      /** Copies */
      copies: number;
      /** Footer Message */
      footer_message: string | null;
      header: components["schemas"]["ShopHeaderResponse"];
    };
    /** RevokedDevicesResponse */
    RevokedDevicesResponse: {
      /** Revoked Sessions */
      revoked_sessions: number;
    };
    /**
     * Role
     * @description Code stable du rôle, relu à chaque requête depuis le rattachement (specs § 8.1).
     * @enum {string}
     */
    Role: "owner" | "seller" | "accountant" | "driver";
    /** RoleResponse */
    RoleResponse: {
      /** Code */
      code: string;
      /** Label */
      label: string;
    };
    /** SettingsPatch */
    SettingsPatch: {
      /** Version */
      version: number;
      receipt_format?: components["schemas"]["ReceiptFormat"] | null;
      /** Paper Width Mm */
      paper_width_mm?: number | null;
      /** Printable Width Mm */
      printable_width_mm?: number | null;
      /** Margin Mm */
      margin_mm?: number | null;
      /** Font Size Pt */
      font_size_pt?: number | null;
      /** Show Logo */
      show_logo?: boolean | null;
      /** Footer Message */
      footer_message?: string | null;
      /** Copies */
      copies?: number | null;
      /** Low Stock Threshold */
      low_stock_threshold?: number | string | null;
      /** Min Price Enabled */
      min_price_enabled?: boolean | null;
      /** Exchange Days */
      exchange_days?: number | null;
      /** Truck Silent Hours */
      truck_silent_hours?: number | null;
      /** Transfer In Transit Days */
      transfer_in_transit_days?: number | null;
      /** Reception Location Id */
      reception_location_id?: string | null;
      /** City */
      city?: string | null;
      /** Phone */
      phone?: string | null;
      /** Address */
      address?: string | null;
      /** Niu */
      niu?: string | null;
      /** Rccm */
      rccm?: string | null;
    };
    /** SettingsResponse */
    SettingsResponse: {
      /** Version */
      version: number;
      /** Receipt Format */
      receipt_format: string;
      /** Print Profile */
      print_profile: string;
      /** Paper Width Mm */
      paper_width_mm: number;
      /** Printable Width Mm */
      printable_width_mm: number;
      /** Margin Mm */
      margin_mm: number;
      /** Font Size Pt */
      font_size_pt: number;
      /** Show Logo */
      show_logo: boolean;
      /** Footer Message */
      footer_message: string | null;
      /** Copies */
      copies: number;
      /** Low Stock Threshold */
      low_stock_threshold: string;
      /** Min Price Enabled */
      min_price_enabled: boolean;
      /** Exchange Days */
      exchange_days: number | null;
      /** Truck Silent Hours */
      truck_silent_hours: number | null;
      /** Transfer In Transit Days */
      transfer_in_transit_days: number | null;
      /** Reception Location Id */
      reception_location_id: string | null;
      header: components["schemas"]["ShopHeaderResponse"];
    };
    /** ShopHeaderResponse */
    ShopHeaderResponse: {
      /** Name */
      name: string;
      /** City */
      city: string;
      /** Phone */
      phone: string;
      /** Address */
      address: string | null;
      /** Niu */
      niu: string | null;
      /** Rccm */
      rccm: string | null;
    };
    /** ShopMembershipResponse */
    ShopMembershipResponse: {
      /** Shop Id */
      shop_id: string;
      /** Shop Name */
      shop_name: string;
      /** Role */
      role: string;
    };
    /**
     * ShopStatus
     * @enum {string}
     */
    ShopStatus: "active" | "closed";
    /** ShopSummaryResponse */
    ShopSummaryResponse: {
      /** Shop Id */
      shop_id: string;
      /** Name */
      name: string;
      /** Profile Code */
      profile_code: string;
      /** City */
      city: string;
      /** Status */
      status: string;
      /** Enabled Modules */
      enabled_modules: string[];
      /** Account Id */
      account_id: string;
      /** Account Name */
      account_name: string;
      /** Plan */
      plan: string;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
    };
    /** TemporaryPinResponse */
    TemporaryPinResponse: {
      /** Temporary Pin */
      temporary_pin: string;
    };
    /**
     * TokenResponse
     * @description Jeton d'accès (gardé en mémoire par le client, § 7.2) ; le refresh part en cookie.
     */
    TokenResponse: {
      /** Access Token */
      access_token: string;
      /**
       * Token Type
       * @default bearer
       * @constant
       */
      token_type: "bearer";
      /**
       * Expires At
       * Format: date-time
       */
      expires_at: string;
      /** Must Change Pin */
      must_change_pin: boolean;
    };
    /** UnreadCountResponse */
    UnreadCountResponse: {
      /** Unread Count */
      unread_count: number;
    };
    /** ValidationError */
    ValidationError: {
      /** Location */
      loc: (string | number)[];
      /** Message */
      msg: string;
      /** Error Type */
      type: string;
      /** Input */
      input?: unknown;
      /** Context */
      ctx?: Record<string, never>;
    };
  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
  health_api_v1_health_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HealthResponse"];
        };
      };
    };
  };
  login_api_v1_auth_login_post: {
    parameters: {
      query?: never;
      header: {
        "x-device-id": string;
      };
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["LoginRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["TokenResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  refresh_api_v1_auth_refresh_post: {
    parameters: {
      query?: never;
      header: {
        "x-device-id": string;
      };
      path?: never;
      cookie?: {
        refresh_token?: string | null;
      };
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["TokenResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  logout_api_v1_auth_logout_post: {
    parameters: {
      query?: never;
      header: {
        "x-device-id": string;
      };
      path?: never;
      cookie?: {
        refresh_token?: string | null;
      };
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      204: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  change_pin_api_v1_auth_change_pin_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ChangePinRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      204: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  me_api_v1_me_get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["MeResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  journal_list_api_v1_shops__shop_id__audit_get: {
    parameters: {
      query?: {
        from?: string | null;
        to?: string | null;
        user_id?: string | null;
        action?: components["schemas"]["AuditAction"][] | null;
        module?: string[] | null;
        cursor?: string | null;
        limit?: number | null;
      };
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AuditPageResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  entity_history_api_v1_shops__shop_id__audit_entities__entity_type___entity_id__get: {
    parameters: {
      query?: {
        cursor?: string | null;
        limit?: number | null;
      };
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        entity_type: string;
        entity_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AuditPageResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  user_activity_api_v1_shops__shop_id__audit_users__user_id__get: {
    parameters: {
      query?: {
        cursor?: string | null;
        limit?: number | null;
      };
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        user_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AuditPageResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  list_alerts_api_v1_shops__shop_id__alerts_get: {
    parameters: {
      query?: {
        unread_only?: boolean;
        cursor?: string | null;
        limit?: number | null;
      };
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AlertPageResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  mark_alert_read_api_v1_shops__shop_id__alerts__alert_id__read_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        alert_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["UnreadCountResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  list_shops_api_v1_platform_shops_get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ShopSummaryResponse"][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  open_shop_api_v1_platform_shops_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["OpenShopRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["OpenedShopResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  get_shop_api_v1_platform_shops__shop_id__get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ShopSummaryResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  administer_shop_api_v1_platform_shops__shop_id__patch: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AdministerShopRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ShopSummaryResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  profile_api_v1_shops__shop_id__profile_get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ProfileResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  get_settings_api_v1_shops__shop_id__settings_get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["SettingsResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  patch_settings_api_v1_shops__shop_id__settings_patch: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["SettingsPatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["SettingsResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  list_locations_api_v1_shops__shop_id__locations_get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["LocationListResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  create_location_api_v1_shops__shop_id__locations_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["LocationCreateRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["LocationResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  patch_location_api_v1_shops__shop_id__locations__location_id__patch: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        location_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["LocationPatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["LocationResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  list_payment_modes_api_v1_shops__shop_id__payment_modes_get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PaymentModeResponse"][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  create_payment_mode_api_v1_shops__shop_id__payment_modes_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["PaymentModeCreateRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PaymentModeResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  patch_payment_mode_api_v1_shops__shop_id__payment_modes__mode_id__patch: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        mode_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["PaymentModePatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PaymentModeResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  list_members_api_v1_shops__shop_id__members_get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["MemberResponse"][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  add_member_api_v1_shops__shop_id__members_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["MemberCreateRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["MemberCreatedResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  patch_member_api_v1_shops__shop_id__members__user_id__patch: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        user_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["MemberPatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["MemberResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  reset_pin_api_v1_shops__shop_id__members__user_id__reset_pin_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        user_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["TemporaryPinResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  revoke_devices_api_v1_shops__shop_id__members__user_id__revoke_devices_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        user_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["RevokedDevicesResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  unlock_api_v1_shops__shop_id__members__user_id__unlock_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        user_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      204: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  admin_access_api_v1_shops__shop_id__admin_access_get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AdminAccessResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  grant_admin_access_api_v1_shops__shop_id__admin_access_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AdminAccessResponse"];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
  revoke_admin_access_api_v1_shops__shop_id__admin_access_delete: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      204: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["HTTPValidationError"];
        };
      };
    };
  };
}
