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
}
export type webhooks = Record<string, never>;
export interface components {
  schemas: {
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
    /** PerformerResponse */
    PerformerResponse: {
      /** User Id */
      user_id: string;
      /** Role */
      role: string;
      /** Device Id */
      device_id: string | null;
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
}
