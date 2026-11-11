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
  "/api/v1/shops/{shop_id}/articles": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Search Articles */
    get: operations["search_articles_api_v1_shops__shop_id__articles_get"];
    put?: never;
    /** Create Article */
    post: operations["create_article_api_v1_shops__shop_id__articles_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/articles/{article_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Article */
    get: operations["get_article_api_v1_shops__shop_id__articles__article_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Patch Article */
    patch: operations["patch_article_api_v1_shops__shop_id__articles__article_id__patch"];
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/articles/{article_id}/prices": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    /** Put Prices */
    put: operations["put_prices_api_v1_shops__shop_id__articles__article_id__prices_put"];
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/articles/{article_id}/archive": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Archive Article */
    post: operations["archive_article_api_v1_shops__shop_id__articles__article_id__archive_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/articles/{article_id}/reactivate": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Reactivate Article */
    post: operations["reactivate_article_api_v1_shops__shop_id__articles__article_id__reactivate_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/expenses": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Expenses */
    get: operations["list_expenses_api_v1_shops__shop_id__expenses_get"];
    put?: never;
    /** Record Expense */
    post: operations["record_expense_api_v1_shops__shop_id__expenses_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/expenses/{expense_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Expense */
    get: operations["get_expense_api_v1_shops__shop_id__expenses__expense_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Correct Expense */
    patch: operations["correct_expense_api_v1_shops__shop_id__expenses__expense_id__patch"];
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/expenses/{expense_id}/cancel": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Cancel Expense */
    post: operations["cancel_expense_api_v1_shops__shop_id__expenses__expense_id__cancel_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/expenses/{expense_id}/repeat": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Repeat Expense */
    get: operations["repeat_expense_api_v1_shops__shop_id__expenses__expense_id__repeat_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/expense-categories": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Categories */
    get: operations["list_categories_api_v1_shops__shop_id__expense_categories_get"];
    put?: never;
    /** Create Category */
    post: operations["create_category_api_v1_shops__shop_id__expense_categories_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/expense-categories/{category_id}": {
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
    /** Patch Category */
    patch: operations["patch_category_api_v1_shops__shop_id__expense_categories__category_id__patch"];
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/tags": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Tags */
    get: operations["list_tags_api_v1_shops__shop_id__tags_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/tags/merge": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Merge Tags */
    post: operations["merge_tags_api_v1_shops__shop_id__tags_merge_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/stock": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Stock Matrix */
    get: operations["stock_matrix_api_v1_shops__shop_id__stock_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/stock/value": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Stock Value */
    get: operations["stock_value_api_v1_shops__shop_id__stock_value_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/stock/damaged": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Damaged Stock */
    get: operations["damaged_stock_api_v1_shops__shop_id__stock_damaged_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/articles/{article_id}/movements": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Article Movements */
    get: operations["article_movements_api_v1_shops__shop_id__articles__article_id__movements_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/adjustments": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Record Adjustment */
    post: operations["record_adjustment_api_v1_shops__shop_id__adjustments_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/inventories": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Start Inventory */
    post: operations["start_inventory_api_v1_shops__shop_id__inventories_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/inventories/{inventory_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Inventory */
    get: operations["get_inventory_api_v1_shops__shop_id__inventories__inventory_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/inventories/{inventory_id}/counts": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    /** Put Counts */
    put: operations["put_counts_api_v1_shops__shop_id__inventories__inventory_id__counts_put"];
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/inventories/{inventory_id}/validate": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Validate Inventory */
    post: operations["validate_inventory_api_v1_shops__shop_id__inventories__inventory_id__validate_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/inventories/{inventory_id}/abandon": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Abandon Inventory */
    post: operations["abandon_inventory_api_v1_shops__shop_id__inventories__inventory_id__abandon_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/suppliers": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Suppliers */
    get: operations["list_suppliers_api_v1_shops__shop_id__suppliers_get"];
    put?: never;
    /** Create Supplier */
    post: operations["create_supplier_api_v1_shops__shop_id__suppliers_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/suppliers/{supplier_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Supplier Sheet */
    get: operations["supplier_sheet_api_v1_shops__shop_id__suppliers__supplier_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Update Supplier */
    patch: operations["update_supplier_api_v1_shops__shop_id__suppliers__supplier_id__patch"];
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/purchases": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Purchases */
    get: operations["list_purchases_api_v1_shops__shop_id__purchases_get"];
    put?: never;
    /** Record Purchase */
    post: operations["record_purchase_api_v1_shops__shop_id__purchases_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/purchases/{purchase_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Purchase */
    get: operations["get_purchase_api_v1_shops__shop_id__purchases__purchase_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Correct Purchase */
    patch: operations["correct_purchase_api_v1_shops__shop_id__purchases__purchase_id__patch"];
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/purchases/{purchase_id}/cancel": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Cancel Purchase */
    post: operations["cancel_purchase_api_v1_shops__shop_id__purchases__purchase_id__cancel_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/purchases/{purchase_id}/payments": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Record Payment */
    post: operations["record_payment_api_v1_shops__shop_id__purchases__purchase_id__payments_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/sales": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** List Sales */
    get: operations["list_sales_api_v1_shops__shop_id__sales_get"];
    put?: never;
    /** Record Sale */
    post: operations["record_sale_api_v1_shops__shop_id__sales_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/sales/{sale_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Sale */
    get: operations["get_sale_api_v1_shops__shop_id__sales__sale_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Modify Sale */
    patch: operations["modify_sale_api_v1_shops__shop_id__sales__sale_id__patch"];
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/sales/{sale_id}/cancel": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Cancel Sale */
    post: operations["cancel_sale_api_v1_shops__shop_id__sales__sale_id__cancel_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/sales/{sale_id}/error-reports": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Report Error */
    post: operations["report_error_api_v1_shops__shop_id__sales__sale_id__error_reports_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/error-reports/{report_id}/reply": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Answer Report */
    post: operations["answer_report_api_v1_shops__shop_id__error_reports__report_id__reply_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/sales/{sale_id}/receipt": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Receipt */
    get: operations["get_receipt_api_v1_shops__shop_id__sales__sale_id__receipt_get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/customers": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Search Customers */
    get: operations["search_customers_api_v1_shops__shop_id__customers_get"];
    put?: never;
    /** Create Customer */
    post: operations["create_customer_api_v1_shops__shop_id__customers_post"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/v1/shops/{shop_id}/customers/{customer_id}": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Customer */
    get: operations["get_customer_api_v1_shops__shop_id__customers__customer_id__get"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Update Customer */
    patch: operations["update_customer_api_v1_shops__shop_id__customers__customer_id__patch"];
    trace?: never;
  };
}
export type webhooks = Record<string, never>;
export interface components {
  schemas: {
    /** AbandonRequest */
    AbandonRequest: {
      /** Version */
      version: number;
    };
    /** AdjustmentRequest */
    AdjustmentRequest: {
      /** Id */
      id?: string | null;
      /** Location Id */
      location_id: string;
      /** Article Id */
      article_id: string;
      /**
       * Direction
       * @enum {string}
       */
      direction: "in" | "out";
      /** Quantity */
      quantity: number | string;
      /**
       * Condition
       * @default sellable
       * @enum {string}
       */
      condition: "sellable" | "damaged";
      /**
       * Reason
       * @enum {string}
       */
      reason:
        | "breakage"
        | "theft"
        | "loss"
        | "entry_error"
        | "sample_or_gift"
        | "supplier_return"
        | "offcut"
        | "other";
      /** Note */
      note?: string | null;
      /** Photo Id */
      photo_id?: string | null;
    };
    /** AdjustmentResponse */
    AdjustmentResponse: {
      /** Id */
      id: string;
      /** Location Id */
      location_id: string;
      /** Article Id */
      article_id: string;
      /** Direction */
      direction: string;
      /** Quantity */
      quantity: string;
      /** Condition */
      condition: string;
      /** Reason */
      reason: string;
      /** Note */
      note: string | null;
      /** Photo Id */
      photo_id: string | null;
      /** Inventory Id */
      inventory_id: string | null;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /** Author Id */
      author_id: string;
      /** Balance After */
      balance_after: string | null;
    };
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
    /** ArticleCreateRequest */
    ArticleCreateRequest: {
      /** Id */
      id?: string | null;
      /** Fields */
      fields?: {
        [key: string]: components["schemas"]["FieldValue"];
      };
      /** Alert Threshold */
      alert_threshold?: number | string | null;
      /** Photo Id */
      photo_id?: string | null;
      /** Notes */
      notes?: string | null;
      /** Base Price */
      base_price?: number | null;
      /** Base Price Piece */
      base_price_piece?: number | null;
      /** Min Price */
      min_price?: number | null;
      /** Min Price Piece */
      min_price_piece?: number | null;
    };
    /** ArticleListResponse */
    ArticleListResponse: {
      /** Items */
      items: components["schemas"]["ArticleResponse"][];
      /** Next Cursor */
      next_cursor: string | null;
    };
    /**
     * ArticleOrder
     * @enum {string}
     */
    ArticleOrder: "name" | "best_selling";
    /** ArticlePatch */
    ArticlePatch: {
      /** Version */
      version: number;
      /** Reason */
      reason?: string | null;
      /** Fields */
      fields?: {
        [key: string]: components["schemas"]["FieldValue"];
      };
      /** Alert Threshold */
      alert_threshold?: number | string | null;
      /** Photo Id */
      photo_id?: string | null;
      /** Notes */
      notes?: string | null;
    };
    /** ArticleResponse */
    ArticleResponse: {
      /** Id */
      id: string;
      /** Version */
      version: number;
      /** Status */
      status: string;
      /** Display Name */
      display_name: string;
      /** Brand */
      brand: string | null;
      /** Model */
      model: string | null;
      /** Reference */
      reference: string | null;
      /** Stock Unit */
      stock_unit: string;
      /** Sold By Piece */
      sold_by_piece: boolean;
      /** Piece Length M */
      piece_length_m: string | null;
      /** Attributes */
      attributes: {
        [key: string]: components["schemas"]["FieldValue"];
      };
      /** Alert Threshold */
      alert_threshold: string | null;
      /** Effective Alert Threshold */
      effective_alert_threshold: string;
      /** Photo Id */
      photo_id: string | null;
      /** Notes */
      notes: string | null;
      /**
       * Created At
       * Format: date-time
       */
      created_at: string;
      /** Base Price */
      base_price?: number | null;
      /** Base Price Piece */
      base_price_piece?: number | null;
      /** Min Price */
      min_price?: number | null;
      /** Min Price Piece */
      min_price_piece?: number | null;
      /** Min Price Active */
      min_price_active?: boolean | null;
      /** Last Cost */
      last_cost?: number | null;
      /** Wac */
      wac?: number | null;
      /** Price History */
      price_history?: components["schemas"]["PriceHistoryResponse"][] | null;
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
    /** CancelSaleRequest */
    CancelSaleRequest: {
      /** Reason */
      reason: string;
      /**
       * Refund Payments
       * @default false
       */
      refund_payments: boolean;
    };
    /** CategoryTotalResponse */
    CategoryTotalResponse: {
      /** Category Id */
      category_id: string;
      /** Amount */
      amount: number;
      /** Count */
      count: number;
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
    /** CountEntry */
    CountEntry: {
      /** Article Id */
      article_id: string;
      /** Counted */
      counted: number | string | null;
    };
    /** CountsRequest */
    CountsRequest: {
      /** Version */
      version: number;
      /** Counts */
      counts: components["schemas"]["CountEntry"][];
    };
    /** CreditRequest */
    CreditRequest: {
      /** Reminder On */
      reminder_on?: string | null;
      /** Terms */
      terms?: string | null;
      /** Guarantor */
      guarantor?: null;
    };
    /** CreditResponse */
    CreditResponse: {
      /** Reminder On */
      reminder_on: string | null;
      /** Terms */
      terms: string | null;
    };
    /** CustomerCreateRequest */
    CustomerCreateRequest: {
      /** Id */
      id?: string | null;
      /** Name */
      name: string;
      /** Phone */
      phone: string;
      /** @default individual */
      kind: components["schemas"]["CustomerKind"];
      /** City */
      city?: string | null;
      /** Address */
      address?: string | null;
      id_doc_type?: components["schemas"]["IdDocumentType"] | null;
      /** Id Doc Number */
      id_doc_number?: string | null;
      /** Id Doc Photo Id */
      id_doc_photo_id?: string | null;
      /** Credit Limit */
      credit_limit?: number | null;
      /** Note */
      note?: string | null;
    };
    /**
     * CustomerKind
     * @enum {string}
     */
    CustomerKind: "individual" | "company";
    /** CustomerListResponse */
    CustomerListResponse: {
      /** Items */
      items: components["schemas"]["CustomerResponse"][];
    };
    /** CustomerPatch */
    CustomerPatch: {
      /** Version */
      version: number;
      /** Name */
      name?: string | null;
      /** Phone */
      phone?: string | null;
      kind?: components["schemas"]["CustomerKind"] | null;
      /** City */
      city?: string | null;
      /** Address */
      address?: string | null;
      id_doc_type?: components["schemas"]["IdDocumentType"] | null;
      /** Id Doc Number */
      id_doc_number?: string | null;
      /** Id Doc Photo Id */
      id_doc_photo_id?: string | null;
      /** Credit Limit */
      credit_limit?: number | null;
      /** Note */
      note?: string | null;
    };
    /** CustomerResponse */
    CustomerResponse: {
      /** Id */
      id: string;
      /** Name */
      name: string;
      /** Phone */
      phone: string;
      /** Kind */
      kind: string;
      /** City */
      city: string | null;
      /** Address */
      address: string | null;
      /** Id Doc Type */
      id_doc_type: string | null;
      /** Id Doc Number */
      id_doc_number: string | null;
      /** Id Doc Photo Id */
      id_doc_photo_id: string | null;
      /** Credit Limit */
      credit_limit: number | null;
      /** Note */
      note: string | null;
      /** Created By */
      created_by: string;
      /** Version */
      version: number;
    };
    /** CustomerSheetResponse */
    CustomerSheetResponse: {
      customer: components["schemas"]["CustomerResponse"];
      /** Total Bought */
      total_bought: number;
      /** Total Due */
      total_due: number;
      /** Sales */
      sales: components["schemas"]["SaleResponse"][];
    };
    /** DamagedLine */
    DamagedLine: {
      /** Article Id */
      article_id: string;
      /** Display Name */
      display_name: string;
      /** Stock Unit */
      stock_unit: string;
      /** Location Id */
      location_id: string;
      /** Location Name */
      location_name: string;
      /** Damaged */
      damaged: string;
      /** Wac */
      wac?: number | null;
      /** Wac Value */
      wac_value?: number | null;
    };
    /** DamagedStockResponse */
    DamagedStockResponse: {
      /** Items */
      items: components["schemas"]["DamagedLine"][];
    };
    /**
     * DetailRequest
     * @description Détail d'une unité vendue (CDC § 17.3) : tous facultatifs.
     */
    DetailRequest: {
      /** Color */
      color?: string | null;
      /** Chassis Number */
      chassis_number?: string | null;
      /** Engine Number */
      engine_number?: string | null;
      /** Size */
      size?: string | null;
    };
    /** DetailResponse */
    DetailResponse: {
      /** Color */
      color: string | null;
      /** Chassis Number */
      chassis_number: string | null;
      /** Engine Number */
      engine_number: string | null;
      /** Size */
      size: string | null;
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
    /**
     * EntryUnit
     * @enum {string}
     */
    EntryUnit: "UNIT" | "PIECE" | "METER" | "YARD";
    /** ErrorReplyRequest */
    ErrorReplyRequest: {
      /** Reply */
      reply: string;
      /**
       * Handled
       * @default true
       */
      handled: boolean;
      /** Version */
      version?: number | null;
    };
    /** ErrorReportRequest */
    ErrorReportRequest: {
      /** Id */
      id?: string | null;
      /** Description */
      description: string;
    };
    /** ErrorReportResponse */
    ErrorReportResponse: {
      /** Id */
      id: string;
      /** Sale Id */
      sale_id: string;
      /** Sale Number */
      sale_number: string;
      /** Description */
      description: string;
      /** Status */
      status: string;
      /** Reported By */
      reported_by: string;
      /**
       * Reported At
       * Format: date-time
       */
      reported_at: string;
      /** Owner Reply */
      owner_reply: string | null;
      /** Replied At */
      replied_at: string | null;
      /** Version */
      version: number;
    };
    /** ExpenseCategoryCreateRequest */
    ExpenseCategoryCreateRequest: {
      /** Id */
      id?: string | null;
      /** Name */
      name: string;
      /** Display Order */
      display_order?: number | null;
    };
    /** ExpenseCategoryPatch */
    ExpenseCategoryPatch: {
      /** Version */
      version: number;
      /** Name */
      name?: string | null;
      /** Active */
      active?: boolean | null;
      /** Display Order */
      display_order?: number | null;
    };
    /** ExpenseCategoryResponse */
    ExpenseCategoryResponse: {
      /** Id */
      id: string;
      /** Name */
      name: string;
      /** Is Base */
      is_base: boolean;
      /** Active */
      active: boolean;
      /** Requires Description */
      requires_description: boolean;
      /** Display Order */
      display_order: number;
      /** Version */
      version: number;
    };
    /** ExpenseCreateRequest */
    ExpenseCreateRequest: {
      /** Id */
      id?: string | null;
      /** Amount */
      amount: number;
      /** Category Id */
      category_id: string;
      /** Spent On */
      spent_on?: string | null;
      /** Payment Mode Id */
      payment_mode_id?: string | null;
      /** Tags */
      tags?: string[];
      /** Description */
      description?: string | null;
      /** Location Id */
      location_id?: string | null;
      /** Beneficiary */
      beneficiary?: string | null;
      /** Attachment Id */
      attachment_id?: string | null;
    };
    /**
     * ExpenseDraftResponse
     * @description Formulaire pré-rempli de « Refaire cette dépense » (rien n'est enregistré).
     */
    ExpenseDraftResponse: {
      /**
       * Spent On
       * Format: date
       */
      spent_on: string;
      /** Amount */
      amount: number;
      /** Category Id */
      category_id: string;
      /** Tags */
      tags: components["schemas"]["TagResponse"][];
      /** Beneficiary */
      beneficiary: string | null;
    };
    /** ExpensePageResponse */
    ExpensePageResponse: {
      /** Items */
      items: components["schemas"]["ExpenseResponse"][];
      /** Next Cursor */
      next_cursor: string | null;
      /**
       * First Day
       * Format: date
       */
      first_day: string;
      /**
       * Last Day
       * Format: date
       */
      last_day: string;
      totals: components["schemas"]["TotalsResponse"];
    };
    /** ExpensePatch */
    ExpensePatch: {
      /** Version */
      version: number;
      /** Amount */
      amount?: number | null;
      /** Category Id */
      category_id?: string | null;
      /** Spent On */
      spent_on?: string | null;
      /** Payment Mode Id */
      payment_mode_id?: string | null;
      /** Tags */
      tags?: string[] | null;
      /** Description */
      description?: string | null;
      /** Location Id */
      location_id?: string | null;
      /** Beneficiary */
      beneficiary?: string | null;
      /** Attachment Id */
      attachment_id?: string | null;
    };
    /** ExpenseResponse */
    ExpenseResponse: {
      /** Id */
      id: string;
      /** Number */
      number: string;
      /**
       * Spent On
       * Format: date
       */
      spent_on: string;
      /** Amount */
      amount: number;
      /** Category Id */
      category_id: string;
      /** Payment Mode Id */
      payment_mode_id: string;
      /** Tags */
      tags: components["schemas"]["TagResponse"][];
      /** Description */
      description: string | null;
      /** Location Id */
      location_id: string | null;
      /** Beneficiary */
      beneficiary: string | null;
      /** Attachment Id */
      attachment_id: string | null;
      /** Status */
      status: string;
      /** Created By */
      created_by: string;
      /** Device Id */
      device_id: string;
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
      cancellation:
        | components["schemas"]["app__interface__http__schemas__expenses__CancellationResponse"]
        | null;
      /** Editable */
      editable: boolean;
      /**
       * Correction Deadline
       * Format: date-time
       */
      correction_deadline: string;
      /** Version */
      version: number;
    };
    /**
     * FeeKind
     * @enum {string}
     */
    FeeKind: "transport" | "customs" | "handling" | "other";
    /** FeeRequest */
    FeeRequest: {
      kind: components["schemas"]["FeeKind"];
      /** Amount */
      amount: number;
      /** Label */
      label?: string | null;
    };
    /** FeeResponse */
    FeeResponse: {
      /** Kind */
      kind: string;
      /** Label */
      label: string | null;
      /** Amount */
      amount: number;
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
    FieldValue: string | number | boolean | null;
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
     * IdDocumentType
     * @enum {string}
     */
    IdDocumentType: "national_id" | "passport" | "driving_license" | "residence_permit" | "other";
    /** InventoryLineResponse */
    InventoryLineResponse: {
      /** Article Id */
      article_id: string;
      /** Display Name */
      display_name: string;
      /** Stock Unit */
      stock_unit: string;
      /** Counted */
      counted: string | null;
      /** Theoretical */
      theoretical?: string | null;
      /** Difference */
      difference?: string | null;
      /** Reason */
      reason?: string | null;
      /** Gap Value */
      gap_value?: number | null;
    };
    /** InventoryResponse */
    InventoryResponse: {
      /** Id */
      id: string;
      /** Number */
      number: string;
      /** Version */
      version: number;
      /** Status */
      status: string;
      /** Location Id */
      location_id: string;
      /** Location Name */
      location_name: string;
      /**
       * Started At
       * Format: date-time
       */
      started_at: string;
      /** Closed At */
      closed_at: string | null;
      /** Global Reason */
      global_reason: string | null;
      /** Sales Since Start */
      sales_since_start: number;
      /** Sales Message */
      sales_message: string | null;
      /** Counted Lines */
      counted_lines: number;
      /** Lines */
      lines: components["schemas"]["InventoryLineResponse"][];
      /** Gap Count */
      gap_count?: number | null;
      /** Gap Value */
      gap_value?: number | null;
    };
    /** InventoryStartRequest */
    InventoryStartRequest: {
      /** Id */
      id?: string | null;
      /** Location Id */
      location_id: string;
    };
    /**
     * LinePatchRequest
     * @description Ligne modifiée, dans l'ordre des lignes : prix et détails ; article / quantité
     *     facultatifs, comparés à ceux de la ligne (différents → `LINE_CHANGE_NOT_ALLOWED`).
     */
    LinePatchRequest: {
      /** Article Id */
      article_id?: string | null;
      /** Quantity */
      quantity?: string | null;
      /** Unit Price */
      unit_price?: number | null;
      /** Details */
      details?: components["schemas"]["DetailRequest"][] | null;
    };
    /** LineRequest */
    LineRequest: {
      /** Article Id */
      article_id: string;
      /** Quantity */
      quantity: string;
      unit?: components["schemas"]["EntryUnit"] | null;
      /** Unit Price */
      unit_price: number;
    };
    /** LineResponse */
    LineResponse: {
      /** Article Id */
      article_id: string;
      /** Quantity */
      quantity: string;
      /** Unit */
      unit: string;
      /** Stock Quantity */
      stock_quantity: string;
      /** Stock Unit */
      stock_unit: string;
      /** Unit Price */
      unit_price: number;
      /** Total */
      total: number;
      /** Fee Share */
      fee_share: number;
      /** Final Unit Cost */
      final_unit_cost: number;
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
    /** LocationValuation */
    LocationValuation: {
      /** Location Id */
      location_id: string;
      /** Location Name */
      location_name: string;
      /** Active */
      active: boolean;
      sellable: components["schemas"]["Valuation"];
      damaged: components["schemas"]["Valuation"];
      incoming: components["schemas"]["Valuation"];
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
    /**
     * MatrixOrder
     * @enum {string}
     */
    MatrixOrder: "name" | "quantity_asc" | "quantity_desc";
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
    /** MovementDocument */
    MovementDocument: {
      /** Type */
      type: string;
      /** Id */
      id: string | null;
      /** Number */
      number: string | null;
    };
    /** MovementListResponse */
    MovementListResponse: {
      /** Article Id */
      article_id: string;
      /** Stock Unit */
      stock_unit: string;
      /** Items */
      items: components["schemas"]["MovementResponse"][];
      /** Next Cursor */
      next_cursor: string | null;
    };
    /** MovementResponse */
    MovementResponse: {
      /** Id */
      id: string;
      /** Type */
      type: string;
      /** Type Label */
      type_label: string;
      /** Location Id */
      location_id: string;
      /** Location Name */
      location_name: string;
      /** Condition */
      condition: string;
      /** Quantity */
      quantity: string;
      /** Balance After */
      balance_after: string;
      document: components["schemas"]["MovementDocument"];
      /**
       * Occurred At
       * Format: date-time
       */
      occurred_at: string;
      /**
       * Recorded At
       * Format: date-time
       */
      recorded_at: string;
      /** Author Id */
      author_id: string;
      /** Stock To Verify */
      stock_to_verify: boolean;
      /** Reverses Id */
      reverses_id: string | null;
      /** Unit Cost */
      unit_cost?: number | null;
    };
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
    /** PaymentRequest */
    PaymentRequest: {
      /** Id */
      id?: string | null;
      /** Amount */
      amount: number;
      /** Mode Id */
      mode_id: string;
      /** Paid On */
      paid_on?: string | null;
      /** Reference */
      reference?: string | null;
    };
    /** PaymentResponse */
    PaymentResponse: {
      /** Id */
      id: string;
      /**
       * Paid On
       * Format: date
       */
      paid_on: string;
      /** Amount */
      amount: number;
      /** Mode Id */
      mode_id: string;
      /** Reference */
      reference: string | null;
      /**
       * Recorded At
       * Format: date-time
       */
      recorded_at: string;
      /** Recorded By */
      recorded_by: string;
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
    /** PriceHistoryResponse */
    PriceHistoryResponse: {
      /** Price Kind */
      price_kind: string;
      /** Old Price */
      old_price: number | null;
      /** New Price */
      new_price: number | null;
      /**
       * Effective At
       * Format: date-time
       */
      effective_at: string;
      /** Author Id */
      author_id: string;
    };
    /**
     * PricesRequest
     * @description `PUT` : les quatre prix remplacés ; un prix absent ou `null` est retiré.
     */
    PricesRequest: {
      /** Version */
      version: number;
      /** Base Price */
      base_price?: number | null;
      /** Base Price Piece */
      base_price_piece?: number | null;
      /** Min Price */
      min_price?: number | null;
      /** Min Price Piece */
      min_price_piece?: number | null;
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
      receipt: components["schemas"]["app__interface__http__schemas__shop__ReceiptResponse"];
      /** Min Price Enabled */
      min_price_enabled: boolean;
      /** Default Location Id */
      default_location_id: string | null;
    };
    /** PurchaseCreateRequest */
    PurchaseCreateRequest: {
      /** Id */
      id?: string | null;
      /** Lines */
      lines: components["schemas"]["LineRequest"][];
      /** Fees */
      fees?: components["schemas"]["FeeRequest"][];
      /** Purchase Date */
      purchase_date?: string | null;
      /** Location Id */
      location_id?: string | null;
      /** Supplier Id */
      supplier_id?: string | null;
      /** Invoice Ref */
      invoice_ref?: string | null;
      /** Invoice Photo Id */
      invoice_photo_id?: string | null;
      /** Note */
      note?: string | null;
      /**
       * Confirm Price Gap
       * @default false
       */
      confirm_price_gap: boolean;
    };
    /** PurchasePageResponse */
    PurchasePageResponse: {
      /** Items */
      items: components["schemas"]["PurchaseResponse"][];
      /** Next Cursor */
      next_cursor: string | null;
      /**
       * First Day
       * Format: date
       */
      first_day: string;
      /**
       * Last Day
       * Format: date
       */
      last_day: string;
      totals: components["schemas"]["PurchaseTotalsResponse"];
    };
    /** PurchasePatch */
    PurchasePatch: {
      /** Version */
      version: number;
      /** Reason */
      reason: string;
      /** Lines */
      lines?: components["schemas"]["LineRequest"][] | null;
      /** Fees */
      fees?: components["schemas"]["FeeRequest"][] | null;
      /** Purchase Date */
      purchase_date?: string | null;
      /** Location Id */
      location_id?: string | null;
      /** Supplier Id */
      supplier_id?: string | null;
      /** Invoice Ref */
      invoice_ref?: string | null;
      /** Invoice Photo Id */
      invoice_photo_id?: string | null;
      /** Note */
      note?: string | null;
      /**
       * Confirm Price Gap
       * @default false
       */
      confirm_price_gap: boolean;
    };
    /** PurchaseResponse */
    PurchaseResponse: {
      /** Id */
      id: string;
      /** Number */
      number: string;
      /** Supplier Id */
      supplier_id: string | null;
      /**
       * Purchase Date
       * Format: date
       */
      purchase_date: string;
      /** Location Id */
      location_id: string;
      /** Invoice Ref */
      invoice_ref: string | null;
      /** Invoice Photo Id */
      invoice_photo_id: string | null;
      /** Note */
      note: string | null;
      /** Lines */
      lines: components["schemas"]["LineResponse"][];
      /** Fees */
      fees: components["schemas"]["FeeResponse"][];
      /** Article Count */
      article_count: number;
      /** Merchandise Total */
      merchandise_total: number;
      /** Fees Total */
      fees_total: number;
      /** Total */
      total: number;
      /** Paid */
      paid: number;
      /** Payment Status */
      payment_status: string;
      /** Payments */
      payments: components["schemas"]["PaymentResponse"][];
      /** Status */
      status: string;
      cancellation:
        | components["schemas"]["app__interface__http__schemas__purchasing__CancellationResponse"]
        | null;
      /** Created By */
      created_by: string;
      /** Device Id */
      device_id: string;
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
      /** Editable */
      editable: boolean;
      /** Cancellable */
      cancellable: boolean;
      /**
       * Last Correction Day
       * Format: date
       */
      last_correction_day: string;
      /** Version */
      version: number;
    };
    /** PurchaseTotalsResponse */
    PurchaseTotalsResponse: {
      /** Count */
      count: number;
      /** Merchandise */
      merchandise: number;
      /** Fees */
      fees: number;
      /** Total */
      total: number;
      /** Paid */
      paid: number;
    };
    /** ReasonEntry */
    ReasonEntry: {
      /** Article Id */
      article_id: string;
      /** Reason */
      reason: string;
    };
    /** ReceiptCustomer */
    ReceiptCustomer: {
      /** Name */
      name: string;
      /** Phone */
      phone: string;
    };
    /**
     * ReceiptFormat
     * @enum {string}
     */
    ReceiptFormat: "58mm" | "80mm" | "a5" | "a4";
    /** ReceiptHeader */
    ReceiptHeader: {
      /** Shop Name */
      shop_name: string;
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
      /** Show Logo */
      show_logo: boolean;
    };
    /** ReceiptLineResponse */
    ReceiptLineResponse: {
      /** Article Name */
      article_name: string;
      /** Sale Mode */
      sale_mode: string;
      /** Quantity */
      quantity: string;
      /** Unit Price */
      unit_price: number;
      /** Line Total */
      line_total: number;
      /** Details */
      details: components["schemas"]["DetailResponse"][];
    };
    /** ReceiptMention */
    ReceiptMention: {
      /** Code */
      code: string;
      /** Label */
      label: string;
    };
    /** ReceiptPaymentResponse */
    ReceiptPaymentResponse: {
      /** Mode Name */
      mode_name: string;
      /** Amount */
      amount: number;
      /** Reference */
      reference: string | null;
    };
    /** ReceiptPrintSettings */
    ReceiptPrintSettings: {
      /** Receipt Format */
      receipt_format: string;
      /** Paper Width Mm */
      paper_width_mm: number;
      /** Printable Width Mm */
      printable_width_mm: number;
      /** Padding Mm */
      padding_mm: number;
      /** Font Size Pt */
      font_size_pt: number;
      /** Copies */
      copies: number;
    };
    /**
     * ReceivableRef
     * @description Créance liée (T17) : `id` posé quand le module Créances l'aura ouverte.
     */
    ReceivableRef: {
      /** Id */
      id: string | null;
      /** Remaining */
      remaining: number;
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
    /** SaleCreateRequest */
    SaleCreateRequest: {
      /** Id */
      id?: string | null;
      /** Location Id */
      location_id?: string | null;
      /** Sold On */
      sold_on?: string | null;
      kind: components["schemas"]["SaleKind"];
      customer?: components["schemas"]["SaleCustomerRequest"] | null;
      /** Lines */
      lines: components["schemas"]["SaleLineRequest"][];
      /** Payments */
      payments?: components["schemas"]["SalePaymentRequest"][];
      credit?: components["schemas"]["CreditRequest"] | null;
      /** Price Request Id */
      price_request_id?: string | null;
      /** Seller Id */
      seller_id?: string | null;
      /** Note */
      note?: string | null;
    };
    /**
     * SaleCustomerRequest
     * @description Client existant (`id`) ou créé à la volée (`id: null` + nom + téléphone + type).
     */
    SaleCustomerRequest: {
      /** Id */
      id?: string | null;
      /** Name */
      name?: string | null;
      /** Phone */
      phone?: string | null;
      /** @default individual */
      kind: components["schemas"]["CustomerKind"];
    };
    /**
     * SaleKind
     * @enum {string}
     */
    SaleKind: "cash" | "credit";
    /** SaleLineRequest */
    SaleLineRequest: {
      /** Article Id */
      article_id: string;
      sale_mode?: components["schemas"]["SaleMode"] | null;
      /** Quantity */
      quantity: string;
      /** Unit Price */
      unit_price: number;
      /** Details */
      details?: components["schemas"]["DetailRequest"][];
    };
    /** SaleLineResponse */
    SaleLineResponse: {
      /** Article Id */
      article_id: string;
      /** Article Name */
      article_name: string;
      /** Sale Mode */
      sale_mode: string;
      /** Quantity */
      quantity: string;
      /** Stock Quantity */
      stock_quantity: string;
      /** Stock Unit */
      stock_unit: string;
      /** Base Price */
      base_price: number | null;
      /** Unit Price */
      unit_price: number;
      /** Line Total */
      line_total: number;
      /** Details */
      details: components["schemas"]["DetailResponse"][];
      /** Frozen Last Cost */
      frozen_last_cost?: number | null;
      /** Frozen Wac */
      frozen_wac?: number | null;
      /** Margin */
      margin?: number | null;
      /** Margin Wac */
      margin_wac?: number | null;
    };
    /**
     * SaleMode
     * @enum {string}
     */
    SaleMode: "unit" | "meter" | "piece";
    /** SalePageResponse */
    SalePageResponse: {
      /** Items */
      items: components["schemas"]["SaleResponse"][];
      /** Next Cursor */
      next_cursor: string | null;
      /** First Day */
      first_day: string | null;
      /** Last Day */
      last_day: string | null;
      totals: components["schemas"]["SaleTotalsResponse"];
    };
    /** SalePatch */
    SalePatch: {
      /** Version */
      version: number;
      /** Reason */
      reason: string;
      /** Lines */
      lines?: components["schemas"]["LinePatchRequest"][] | null;
      /** Payments */
      payments?: components["schemas"]["SalePaymentRequest"][] | null;
      customer?: components["schemas"]["SaleCustomerRequest"] | null;
      /** Sold On */
      sold_on?: string | null;
      /** Note */
      note?: string | null;
    };
    /** SalePaymentRequest */
    SalePaymentRequest: {
      /** Id */
      id?: string | null;
      /** Mode Id */
      mode_id: string;
      /** Amount */
      amount: number;
      /** Reference */
      reference?: string | null;
    };
    /** SalePaymentResponse */
    SalePaymentResponse: {
      /** Id */
      id: string;
      /** Mode Id */
      mode_id: string;
      /** Amount */
      amount: number;
      /** Reference */
      reference: string | null;
      /** Nature */
      nature: string;
    };
    /** SaleResponse */
    SaleResponse: {
      /** Id */
      id: string;
      /** Number */
      number: string;
      /** Provisional Number */
      provisional_number: string | null;
      /** Status */
      status: string;
      /** Kind */
      kind: string;
      /**
       * Sold On
       * Format: date
       */
      sold_on: string;
      /**
       * Sold At
       * Format: date-time
       */
      sold_at: string;
      /** Location Id */
      location_id: string;
      /** Seller Id */
      seller_id: string;
      /** Customer Id */
      customer_id: string | null;
      /** Total */
      total: number;
      /** Paid */
      paid: number;
      /** Remaining */
      remaining: number;
      receivable: components["schemas"]["ReceivableRef"] | null;
      /** Lines */
      lines: components["schemas"]["SaleLineResponse"][];
      /** Payments */
      payments: components["schemas"]["SalePaymentResponse"][];
      credit: components["schemas"]["CreditResponse"] | null;
      /** Note */
      note: string | null;
      /** Stock To Verify */
      stock_to_verify: boolean;
      cancellation:
        components["schemas"]["app__interface__http__schemas__sales__CancellationResponse"] | null;
      /** Created By */
      created_by: string;
      /** Device Id */
      device_id: string;
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
      /** Editable */
      editable: boolean;
      /** Version */
      version: number;
      /** Warnings */
      warnings: components["schemas"]["WarningResponse"][];
      /** Error Reports */
      error_reports: components["schemas"]["ErrorReportResponse"][];
    };
    /** SaleTotalsResponse */
    SaleTotalsResponse: {
      /** Count */
      count: number;
      /** Total */
      total: number;
      /** Paid */
      paid: number;
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
    /** StockCell */
    StockCell: {
      /** Location Id */
      location_id: string;
      /** Sellable */
      sellable: string;
      /** Damaged */
      damaged: string;
    };
    /** StockColumn */
    StockColumn: {
      /** Location Id */
      location_id: string;
      /** Name */
      name: string;
      /** Kind */
      kind: string;
      /** Is Point Of Sale */
      is_point_of_sale: boolean;
    };
    /** StockMatrixResponse */
    StockMatrixResponse: {
      /** Locations */
      locations: components["schemas"]["StockColumn"][];
      /** Items */
      items: components["schemas"]["StockRow"][];
    };
    /** StockRow */
    StockRow: {
      /** Article Id */
      article_id: string;
      /** Display Name */
      display_name: string;
      /** Stock Unit */
      stock_unit: string;
      /** Cells */
      cells: components["schemas"]["StockCell"][];
      /** Incoming */
      incoming: string;
      /** Total */
      total: string;
      /**
       * Stock Status
       * @enum {string}
       */
      stock_status: "ok" | "low" | "out";
      /** Alert Threshold */
      alert_threshold: string;
      /** Base Price */
      base_price?: number | null;
      /** Last Cost */
      last_cost?: number | null;
      /** Wac */
      wac?: number | null;
      /** Wac Value */
      wac_value?: number | null;
    };
    /** StockValueResponse */
    StockValueResponse: {
      /** Locations */
      locations: components["schemas"]["LocationValuation"][];
      sellable: components["schemas"]["Valuation"];
      damaged: components["schemas"]["Valuation"];
      incoming: components["schemas"]["Valuation"];
    };
    /** SupplierListResponse */
    SupplierListResponse: {
      /** Items */
      items: components["schemas"]["SupplierResponse"][];
    };
    /** SupplierPatch */
    SupplierPatch: {
      /** Version */
      version: number;
      /** Name */
      name?: string | null;
      /** Phone */
      phone?: string | null;
      /** City */
      city?: string | null;
      /** Country */
      country?: string | null;
      /** Note */
      note?: string | null;
      /** Active */
      active?: boolean | null;
    };
    /** SupplierRequest */
    SupplierRequest: {
      /** Id */
      id?: string | null;
      /** Name */
      name: string;
      /** Phone */
      phone?: string | null;
      /** City */
      city?: string | null;
      /** Country */
      country?: string | null;
      /** Note */
      note?: string | null;
    };
    /** SupplierResponse */
    SupplierResponse: {
      /** Id */
      id: string;
      /** Name */
      name: string;
      /** Phone */
      phone: string | null;
      /** City */
      city: string | null;
      /** Country */
      country: string | null;
      /** Note */
      note: string | null;
      /** Active */
      active: boolean;
      /** Version */
      version: number;
    };
    /** SupplierSheetResponse */
    SupplierSheetResponse: {
      supplier: components["schemas"]["SupplierResponse"];
      /**
       * First Day
       * Format: date
       */
      first_day: string;
      /**
       * Last Day
       * Format: date
       */
      last_day: string;
      totals: components["schemas"]["PurchaseTotalsResponse"];
      /** Purchases */
      purchases: components["schemas"]["PurchaseResponse"][];
    };
    /** TagMergeRequest */
    TagMergeRequest: {
      /** Source Id */
      source_id: string;
      /** Target Id */
      target_id: string;
    };
    /** TagMergeResponse */
    TagMergeResponse: {
      target: components["schemas"]["TagResponse"];
      /** Retagged Expenses */
      retagged_expenses: number;
    };
    /** TagResponse */
    TagResponse: {
      /** Id */
      id: string;
      /** Name */
      name: string;
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
    /** TotalsResponse */
    TotalsResponse: {
      /** Amount */
      amount: number;
      /** Count */
      count: number;
      /** By Category */
      by_category: components["schemas"]["CategoryTotalResponse"][];
    };
    /** UnreadCountResponse */
    UnreadCountResponse: {
      /** Unread Count */
      unread_count: number;
    };
    /** ValidateRequest */
    ValidateRequest: {
      /** Version */
      version: number;
      /** Reasons */
      reasons?: components["schemas"]["ReasonEntry"][];
      /** Global Reason */
      global_reason?: string | null;
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
    /** Valuation */
    Valuation: {
      /** At Wac */
      at_wac: number | null;
      /** At Wac Known */
      at_wac_known: number;
      /** Without Wac */
      without_wac: number;
      /** At Last Cost */
      at_last_cost: number | null;
      /** At Last Cost Known */
      at_last_cost_known: number;
      /** Without Last Cost */
      without_last_cost: number;
    };
    /** WarningResponse */
    WarningResponse: {
      /** Code */
      code: string;
      /** Message */
      message: string;
      /** Details */
      details: {
        [key: string]: unknown;
      };
    };
    /** CancelRequest */
    app__interface__http__schemas__expenses__CancelRequest: {
      /** Reason */
      reason: string;
    };
    /** CancellationResponse */
    app__interface__http__schemas__expenses__CancellationResponse: {
      /**
       * Cancelled At
       * Format: date-time
       */
      cancelled_at: string;
      /** Cancelled By */
      cancelled_by: string;
      /** Reason */
      reason: string;
    };
    /** CancelRequest */
    app__interface__http__schemas__purchasing__CancelRequest: {
      /** Reason */
      reason: string;
    };
    /** CancellationResponse */
    app__interface__http__schemas__purchasing__CancellationResponse: {
      /**
       * Cancelled At
       * Format: date-time
       */
      cancelled_at: string;
      /** Cancelled By */
      cancelled_by: string;
      /** Reason */
      reason: string;
    };
    /** ReceiptResponse */
    app__interface__http__schemas__receipts__ReceiptResponse: {
      /** Title */
      title: string;
      header: components["schemas"]["ReceiptHeader"];
      /** Sale Id */
      sale_id: string;
      /** Number */
      number: string;
      /** Provisional Number */
      provisional_number: string | null;
      /**
       * Sold At
       * Format: date-time
       */
      sold_at: string;
      /** Seller Name */
      seller_name: string;
      customer: components["schemas"]["ReceiptCustomer"] | null;
      /** Lines */
      lines: components["schemas"]["ReceiptLineResponse"][];
      /** Total */
      total: number;
      /** Paid */
      paid: number;
      /** Payments */
      payments: components["schemas"]["ReceiptPaymentResponse"][];
      /** Remaining */
      remaining: number;
      /** Mentions */
      mentions: components["schemas"]["ReceiptMention"][];
      /** Footer Message */
      footer_message: string | null;
      printing: components["schemas"]["ReceiptPrintSettings"];
      /** Print Sequence */
      print_sequence: number;
      /**
       * Printed At
       * Format: date-time
       */
      printed_at: string;
    };
    /** CancellationResponse */
    app__interface__http__schemas__sales__CancellationResponse: {
      /**
       * Cancelled At
       * Format: date-time
       */
      cancelled_at: string;
      /** Cancelled By */
      cancelled_by: string;
      /** Reason */
      reason: string;
    };
    /** ReceiptResponse */
    app__interface__http__schemas__shop__ReceiptResponse: {
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
  search_articles_api_v1_shops__shop_id__articles_get: {
    parameters: {
      query?: {
        q?: string | null;
        status?: string;
        sort?: components["schemas"]["ArticleOrder"];
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
          "application/json": components["schemas"]["ArticleListResponse"];
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
  create_article_api_v1_shops__shop_id__articles_post: {
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
        "application/json": components["schemas"]["ArticleCreateRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ArticleResponse"];
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
  get_article_api_v1_shops__shop_id__articles__article_id__get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        article_id: string;
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
          "application/json": components["schemas"]["ArticleResponse"];
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
  patch_article_api_v1_shops__shop_id__articles__article_id__patch: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        article_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ArticlePatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ArticleResponse"];
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
  put_prices_api_v1_shops__shop_id__articles__article_id__prices_put: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        article_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["PricesRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ArticleResponse"];
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
  archive_article_api_v1_shops__shop_id__articles__article_id__archive_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        article_id: string;
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
          "application/json": components["schemas"]["ArticleResponse"];
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
  reactivate_article_api_v1_shops__shop_id__articles__article_id__reactivate_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        article_id: string;
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
          "application/json": components["schemas"]["ArticleResponse"];
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
  list_expenses_api_v1_shops__shop_id__expenses_get: {
    parameters: {
      query?: {
        from?: string | null;
        to?: string | null;
        category_id?: string | null;
        tag_id?: string | null;
        location_id?: string | null;
        user_id?: string | null;
        payment_mode_id?: string | null;
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
          "application/json": components["schemas"]["ExpensePageResponse"];
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
  record_expense_api_v1_shops__shop_id__expenses_post: {
    parameters: {
      query?: never;
      header: {
        "x-captured-at"?: string | null;
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
        "application/json": components["schemas"]["ExpenseCreateRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ExpenseResponse"];
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
  get_expense_api_v1_shops__shop_id__expenses__expense_id__get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        expense_id: string;
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
          "application/json": components["schemas"]["ExpenseResponse"];
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
  correct_expense_api_v1_shops__shop_id__expenses__expense_id__patch: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        expense_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ExpensePatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ExpenseResponse"];
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
  cancel_expense_api_v1_shops__shop_id__expenses__expense_id__cancel_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        expense_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["app__interface__http__schemas__expenses__CancelRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ExpenseResponse"];
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
  repeat_expense_api_v1_shops__shop_id__expenses__expense_id__repeat_get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        expense_id: string;
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
          "application/json": components["schemas"]["ExpenseDraftResponse"];
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
  list_categories_api_v1_shops__shop_id__expense_categories_get: {
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
          "application/json": components["schemas"]["ExpenseCategoryResponse"][];
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
  create_category_api_v1_shops__shop_id__expense_categories_post: {
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
        "application/json": components["schemas"]["ExpenseCategoryCreateRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ExpenseCategoryResponse"];
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
  patch_category_api_v1_shops__shop_id__expense_categories__category_id__patch: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        category_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ExpenseCategoryPatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ExpenseCategoryResponse"];
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
  list_tags_api_v1_shops__shop_id__tags_get: {
    parameters: {
      query?: {
        search?: string | null;
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
          "application/json": components["schemas"]["TagResponse"][];
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
  merge_tags_api_v1_shops__shop_id__tags_merge_post: {
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
        "application/json": components["schemas"]["TagMergeRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["TagMergeResponse"];
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
  stock_matrix_api_v1_shops__shop_id__stock_get: {
    parameters: {
      query?: {
        q?: string | null;
        location_id?: string | null;
        sort?: components["schemas"]["MatrixOrder"];
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
          "application/json": components["schemas"]["StockMatrixResponse"];
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
  stock_value_api_v1_shops__shop_id__stock_value_get: {
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
          "application/json": components["schemas"]["StockValueResponse"];
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
  damaged_stock_api_v1_shops__shop_id__stock_damaged_get: {
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
          "application/json": components["schemas"]["DamagedStockResponse"];
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
  article_movements_api_v1_shops__shop_id__articles__article_id__movements_get: {
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
        article_id: string;
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
          "application/json": components["schemas"]["MovementListResponse"];
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
  record_adjustment_api_v1_shops__shop_id__adjustments_post: {
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
        "application/json": components["schemas"]["AdjustmentRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AdjustmentResponse"];
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
  start_inventory_api_v1_shops__shop_id__inventories_post: {
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
        "application/json": components["schemas"]["InventoryStartRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InventoryResponse"];
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
  get_inventory_api_v1_shops__shop_id__inventories__inventory_id__get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        inventory_id: string;
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
          "application/json": components["schemas"]["InventoryResponse"];
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
  put_counts_api_v1_shops__shop_id__inventories__inventory_id__counts_put: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        inventory_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["CountsRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InventoryResponse"];
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
  validate_inventory_api_v1_shops__shop_id__inventories__inventory_id__validate_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        inventory_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ValidateRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InventoryResponse"];
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
  abandon_inventory_api_v1_shops__shop_id__inventories__inventory_id__abandon_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        inventory_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AbandonRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["InventoryResponse"];
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
  list_suppliers_api_v1_shops__shop_id__suppliers_get: {
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
          "application/json": components["schemas"]["SupplierListResponse"];
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
  create_supplier_api_v1_shops__shop_id__suppliers_post: {
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
        "application/json": components["schemas"]["SupplierRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["SupplierResponse"];
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
  supplier_sheet_api_v1_shops__shop_id__suppliers__supplier_id__get: {
    parameters: {
      query?: {
        from?: string | null;
        to?: string | null;
      };
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        supplier_id: string;
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
          "application/json": components["schemas"]["SupplierSheetResponse"];
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
  update_supplier_api_v1_shops__shop_id__suppliers__supplier_id__patch: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        supplier_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["SupplierPatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["SupplierResponse"];
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
  list_purchases_api_v1_shops__shop_id__purchases_get: {
    parameters: {
      query?: {
        from?: string | null;
        to?: string | null;
        supplier_id?: string | null;
        article_id?: string | null;
        location_id?: string | null;
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
          "application/json": components["schemas"]["PurchasePageResponse"];
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
  record_purchase_api_v1_shops__shop_id__purchases_post: {
    parameters: {
      query?: never;
      header: {
        "x-captured-at"?: string | null;
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
        "application/json": components["schemas"]["PurchaseCreateRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PurchaseResponse"];
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
  get_purchase_api_v1_shops__shop_id__purchases__purchase_id__get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        purchase_id: string;
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
          "application/json": components["schemas"]["PurchaseResponse"];
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
  correct_purchase_api_v1_shops__shop_id__purchases__purchase_id__patch: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        purchase_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["PurchasePatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PurchaseResponse"];
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
  cancel_purchase_api_v1_shops__shop_id__purchases__purchase_id__cancel_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        purchase_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["app__interface__http__schemas__purchasing__CancelRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PurchaseResponse"];
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
  record_payment_api_v1_shops__shop_id__purchases__purchase_id__payments_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        purchase_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["PaymentRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PurchaseResponse"];
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
  list_sales_api_v1_shops__shop_id__sales_get: {
    parameters: {
      query?: {
        from?: string | null;
        to?: string | null;
        seller_id?: string | null;
        article_id?: string | null;
        payment_mode_id?: string | null;
        kind?: components["schemas"]["SaleKind"] | null;
        q?: string | null;
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
          "application/json": components["schemas"]["SalePageResponse"];
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
  record_sale_api_v1_shops__shop_id__sales_post: {
    parameters: {
      query?: never;
      header: {
        "x-captured-at"?: string | null;
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
        "application/json": components["schemas"]["SaleCreateRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["SaleResponse"];
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
  get_sale_api_v1_shops__shop_id__sales__sale_id__get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        sale_id: string;
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
          "application/json": components["schemas"]["SaleResponse"];
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
  modify_sale_api_v1_shops__shop_id__sales__sale_id__patch: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        sale_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["SalePatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["SaleResponse"];
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
  cancel_sale_api_v1_shops__shop_id__sales__sale_id__cancel_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        sale_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["CancelSaleRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["SaleResponse"];
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
  report_error_api_v1_shops__shop_id__sales__sale_id__error_reports_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        sale_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ErrorReportRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorReportResponse"];
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
  answer_report_api_v1_shops__shop_id__error_reports__report_id__reply_post: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        report_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["ErrorReplyRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ErrorReportResponse"];
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
  get_receipt_api_v1_shops__shop_id__sales__sale_id__receipt_get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        sale_id: string;
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
          "application/json": components["schemas"]["app__interface__http__schemas__receipts__ReceiptResponse"];
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
  search_customers_api_v1_shops__shop_id__customers_get: {
    parameters: {
      query?: {
        q?: string | null;
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
          "application/json": components["schemas"]["CustomerListResponse"];
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
  create_customer_api_v1_shops__shop_id__customers_post: {
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
        "application/json": components["schemas"]["CustomerCreateRequest"];
      };
    };
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["CustomerResponse"];
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
  get_customer_api_v1_shops__shop_id__customers__customer_id__get: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        customer_id: string;
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
          "application/json": components["schemas"]["CustomerSheetResponse"];
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
  update_customer_api_v1_shops__shop_id__customers__customer_id__patch: {
    parameters: {
      query?: never;
      header: {
        authorization?: string | null;
        "x-device-id": string;
      };
      path: {
        customer_id: string;
        shop_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["CustomerPatch"];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["CustomerResponse"];
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
