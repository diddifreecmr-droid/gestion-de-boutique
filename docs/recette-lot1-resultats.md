# Résultats de la recette — Lot 1 (T24)

> Auteur : @qa · 12/11/2026 · Branche `wip/t24-recette` · Référence : `docs/recette-lot1.md`, `specs.md` § 12.2.
> **Périmètre décidé par l'utilisateur** : tests **unitaires et d'intégration** seulement (pas d'E2E, pas de
> Chromium). Les parcours Playwright (§ 5), l'accessibilité axe sur navigateur réel, Lighthouse et les tests terrain
> sont donc classés **hors CI** ; leurs équivalents unitaires existants sont cités quand il y en a.
> Les décisions de `specs.md` § 15.1 priment sur les valeurs « à confirmer » de la recette ; elles ne sont pas modifiées.

## 0. Légende et chemins

| Statut | Sens |
| --- | --- |
| **couvert** | au moins un test automatisé vérifie le résultat attendu (valeur ou code exact) |
| **partiel** | une partie seulement est vérifiée, ou à un autre niveau que celui demandé (voir la note) |
| **manquant** | aucun test, ou fonction non livrée |
| **hors CI** | E2E Playwright, mesure navigateur ou test terrain : exclu du périmètre T24 |

Chemins : `bt/` = `backend/tests/`, `fs/` = `frontend/src/`, **`R/` = `backend/tests/http/recette/` (nouveau, T24)**.
`R/` assemble l'application **complète** comme `build_app` et tourne sur mémoire **et** sur PostgreSQL
(`uv run pytest tests/http/recette --backend=postgres`). Jeu `R/world.py` : boutiques A et B remplies par l'API, coût
sentinelle 543 210, prix sentinelle 777 777, utilisateur U vendeur dans A et comptable dans B.

## 1. Synthèse

| Ensemble | Cas | Avant T24 : couvert / partiel / manquant / hors CI | Après T24 : couvert / partiel / manquant / hors CI |
| --- | --- | --- | --- |
| Cas fonctionnels (§ 1, identifiants PLT … AUD) | 134 | 116 / 10 / 5 / 3 | 120 / 9 / 2 / 3 |
| Scénarios chiffrés SCN-01 à 10 | 10 | 9 / 1 / 0 / 0 | 10 / 0 / 0 / 0 |
| Matrice des droits SEC-M01 à M30 | 30 | 2 / 28 / 0 / 0 | 30 / 0 / 0 / 0 |
| Non-fuite SEC-N01 à 06 | 6 | 2 / 3 / 1 / 0 | 5 / 0 / 1 / 0 |
| Isolation SEC-I01 à 14 | 14 | 4 / 5 / 5 / 0 | 13 / 0 / 1 / 0 |
| Blocage, révocation, désactivation SEC-L, R, X | 21 | 20 / 1 / 0 / 0 | 20 / 1 / 0 / 0 |
| Erreurs par code ERR-* | 49 | 40 / 9 / 0 / 0 | 48 / 1 / 0 / 0 |
| Hors-ligne OFF-01 à 10 | 10 | 10 / 0 / 0 / 0 | 10 / 0 / 0 / 0 |
| Parcours E2E-01 à 10, A11Y-01 à 07, PERF-01 à 06 | 23 | 2 / 6 / 1 / 14 | 2 / 6 / 1 / 14 |
| **Total** | **297** | **205 / 63 / 12 / 17** | **258 / 17 / 5 / 17** |

La recette annonçait « 139 cas fonctionnels » : le décompte inclut 5 renvois « UC-STK-06 à 10 » qui ne sont pas des cas ;
134 identifiants distincts sont tracés ici. Critères d'acceptation : voir § 2.

**Défauts trouvés et corrigés** (détail § 4) :

1. `POST /sync` et `GET /offline-snapshot` : l'administrateur **sans délégation** recevait `403 FEATURE_DISABLED`
   au lieu de `404` (specs § 8.3) ; avec le droit `offline_capture` ouvert, son envoi aurait été traité et ses
   opérations refusées **écrites** dans la boutique (trace, journal, alerte au propriétaire).
2. `POST /customers/{id}/installments` avec le client d'une autre boutique (ou inconnu) : `400 VALIDATION_ERROR`
   au lieu de `404`.

## 2. Critères d'acceptation A1 à A10

| # | Critère | Tests | Statut |
| --- | --- | --- | --- |
| A1 | Vente comptant en 4 gestes, < 30 s, 360 px | `fs/features/sales/NewSalePage.cash.test.tsx` « se fait en 4 gestes : article, prix, paiement, valider » ; `NewSalePage.owner.test.tsx` (360 px sans débordement) | **partiel** — les gestes sont comptés en jsdom ; le chronomètre et le téléphone réel sont hors CI |
| A2 | Parcours § 17.5 : 780 000 / 300 000 / 240 000 / 480 000 / 540 000 | **`R/test_scn01_reference_http.py`** (achat → vente → lecture par rôle → tableau de bord → créance → reçu, mémoire et PostgreSQL) ; `bt/application/sales/test_record_sale.py::test_scn01_…`, `bt/application/receivables/test_sale_link.py::test_scn01_…`, `bt/domain/purchasing/test_costing.py::test_scn01_…` | **couvert** (avant : partiel, le tableau de bord SCN-01 7c n'était pas vérifié) |
| A3 | CMP 10 × 500 000 + 5 × 530 000 → 510 000 | `bt/domain/purchasing/test_costing.py::test_scn02_wac_and_rounding_rule`, `bt/application/purchasing/test_record_purchase.py::test_scn02_…` | **couvert** |
| A4 | Le vendeur ne reçoit aucun coût sur aucune route | **`R/test_no_leak_http.py`** : balayage de toutes les routes de lecture de l'OpenAPI, réponses d'écriture et d'erreur, clés et valeurs sentinelles, garde-fou « route non déclarée » | **couvert** (avant : partiel, routes par module) |
| A5 | B ne lit ni ne modifie jamais A | **`R/test_isolation_http.py`** (toutes les routes, non-membre, admin sans délégation, objets de B par le chemin de A, références étrangères dans les corps, versions de B inchangées) ; **`bt/contracts/test_port_signatures.py`** ; contrats `test_shop_b_never_reads_shop_a` (mémoire + PostgreSQL) | **couvert** (avant : partiel) |
| A6 | Hors-ligne inactif : « Connexion nécessaire », rien en file, `/sync` 403 ; actif : provisoire → définitif | `bt/http/sync/test_sync_disabled_http.py`, `test_sync_operations_http.py` ; `fs/features/sales/NewSalePage.offline.test.tsx`, `fs/core/offline/*.test.ts`, `fs/app/OfflineQueue.test.tsx` | **couvert** en intégration ; la variante navigateur (`setOffline`) est hors CI |
| A7 | Toute action RG-T01 journalisée ; aucune route ne modifie le journal | **`R/test_journal_writes_http.py`** (chaque écriture réussie de l'OpenAPI ajoute ≥ 1 entrée ; aucune route `DELETE` métier) ; `bt/contracts/test_audit_contract.py::test_port_exposes_no_way_to_modify_or_delete`, `test_audit_recorder_contract.py` | **couvert** — sauf le refus `UPDATE/DELETE` au niveau des droits PostgreSQL (AUD-08, écart E5) |
| A8 | Numéros continus sous 20 ventes concurrentes | **`bt/infrastructure/postgres/test_sales_numbering.py`** (20 `RecordSale` réellement concurrents : `V-000001` à `V-000020`, aucun conflit renvoyé, 20 sorties de stock) ; `test_concurrency.py::test_20_concurrent_sales_get_continuous_gapless_numbers` (allocateur) | **couvert** (avant : partiel, allocateur seul) |
| A9 | Domaine et application passent sans PostgreSQL | job `backend` de `.github/workflows/ci.yml` (`pytest --cov` sur mémoire) ; `lint-imports` (l'application n'importe pas l'infrastructure) | **couvert** |
| A10 | Matrice § 4.2 cellule par cellule | `bt/application/security/test_role_matrix.py` (Policy, 2ᵉ saisie indépendante) + **`R/test_rights_matrix_http.py`** (30 lignes × 4 rôles en appels HTTP réels, 1 entrée « Accès refusé » par 403) | **couvert** (avant : partiel, Policy seule) |

## 3. Écarts restants qui demandent une décision

| # | Écart | Cas touchés | Proposition |
| --- | --- | --- | --- |
| E1 | **Pièces jointes non livrées** : `POST /attachments` et `GET /attachments/{id}/url` (specs § 6.3, Lot 1 ; TR-17) n'existent pas ; les champs `*_photo_id` / `attachment_ids` sont acceptés sans route d'envoi | ATT-01, SEC-N06, SEC-I14, GUA-01, SAL-08, CUS-03 | tâche dédiée (port `FileStorage` + MinIO/Silo) avant la mise en service, ou report au Lot 2 acté dans specs |
| E2 | **« Partager » (PDF) non livré** : bouton désactivé « Partage PDF : à venir » | RCP-05, PERF-03 | livrer le module PDF chargé à la demande, ou le reporter explicitement |
| E3 | **Écrans non livrés** (page « à venir ») : Alertes (cloche), Journal, Clients, Réglages de la boutique (membres, lieux, modes, réglages), console plateforme « Boutiques » ; l'API correspondante est livrée et testée | ALR-02, AUD-01 (affichage), PLT-05, SET-03 (affichage), UC-SOC-04/05/06 côté écran | planifier ces écrans avant la mise en service (le propriétaire ne peut sinon ni ajouter un vendeur ni régler la boutique depuis l'application) |
| E4 | M16 : la recette attend `422 PRICE_BELOW_MINIMUM` pour le vendeur ; la décision § 15.1 l'accepte avec un avertissement | SEC-M16, ERR-PRM-01 | aucune : les tests suivent § 15.1 ; mettre à jour la recette |
| E5 | AUD-08 : aucune protection du journal **dans PostgreSQL** (pas de `REVOKE UPDATE, DELETE` ni de déclencheur sur `audit_entry`) ; seule l'API l'interdit | AUD-08, RG-J01 | rôle de base séparé pour l'API au déploiement (T25) + test de refus de permission |
| E6 | Clés « interdites » de la recette SEC-N02 trop larges : l'inventaire en cours expose au comptable `sales_since_start` et `sales_message` (exigés par UC-STK-07 / INV-06) ; noms de réglages (`margin_mm`, `min_price_enabled`…) | SEC-N02, SEC-N03 | accepter ces exceptions (listées dans `R/test_no_leak_http.py`) ; les valeurs sentinelles, elles, ne fuient jamais |
| E7 | Admin **avec** délégation : `/sync` le laisse passer (lecture accordée) ; chaque opération est alors refusée par le cas d'utilisation, mais **tracée** comme « Saisie refusée » | — (droit `offline_capture` inactif en V1) | refuser l'écriture `/sync` à tout administrateur, à trancher avec l'ouverture du hors-ligne |
| E8 | 51 questions Q-01 à Q-51 de la recette : celles tranchées par § 15.1 (Q-01, Q-02, Q-09, Q-51, Q7, Q8, changement de code, prix minimum, échange à crédit) sont testées selon la décision ; pour les autres, les tests figent le comportement **actuel** (noté « selon l'implémentation ») ou le cas reste « partiel » | MOD-03 [Q-06], ERR-VER-02, SEC-X03, INV-06 [Q-17], LOW-01 [Q-18], ERR-PRM-07 [Q-44] | confirmer ou corriger ces comportements (recette § 6) |

## 4. Défauts trouvés et corrigés

| # | Constat (test qui l'a révélé) | Correction |
| --- | --- | --- |
| D1 | `R/test_isolation_http.py::test_shop_b_is_not_found_for_a_non_member_and_for_the_admin` : l'admin sans délégation recevait `403 FEATURE_DISABLED` sur `/sync` et `/offline-snapshot` (le droit d'offre était lu avant l'accès à la boutique) | `SyncOperations` et `ReadOfflineSnapshot` vérifient d'abord l'accès (`Policy.require(HOME_READ)` → 404), puis le droit d'offre ; `Policy` injectée dans `SyncOperations` (`app/bootstrap/sync.py`) |
| D2 | `R/test_isolation_http.py::test_objects_of_b_are_not_found_through_shop_a` : versement par client d'une autre boutique → `400` | `RecordInstallment` charge d'abord le client (`CustomerRepository.get` → 404) |

## 5. Détail par cas

### 5.1 Cas fonctionnels (recette § 1)

| Cas | Test(s) | Avant | Après | Note |
| --- | --- | --- | --- | --- |
| PLT-01 | `bt/application/shops/test_open_shop.py::test_motos_shop_gets_the_profile_defaults` ; `bt/http/shops/test_shops_http.py::test_platform_console` | couvert | couvert | |
| PLT-02 | `test_open_shop.py::test_known_phone_is_attached_without_duplicate_or_new_code` | couvert | couvert | |
| PLT-03 | `test_open_shop.py::test_invalid_inputs_are_refused_before_any_write` ; `test_shops_http.py::test_platform_console` (`details.fields`) | couvert | couvert | |
| PLT-04 | `test_open_shop.py::test_only_the_platform_admin_opens_a_shop` ; `R/test_rights_matrix_http.py::test_m28_me_and_m29_platform_console` | couvert | couvert | |
| PLT-05 | `fs/app/routes.test.tsx` (accès administrateur) | hors CI | hors CI | E2E ; écran « Boutiques » non livré (E3) |
| AUTH-01 | `bt/http/auth/test_login_http.py::test_login_sets_an_httponly_refresh_cookie_and_returns_the_access_token` | couvert | couvert | |
| AUTH-02 | `bt/application/identity/test_authenticate.py::test_temporary_code_blocks_shop_routes_but_not_identity` ; `bt/http/auth/test_session_http.py::test_first_login_flow_requires_a_pin_change` | couvert | couvert | |
| AUTH-03 | `fs/core/auth/session.test.ts` « plusieurs 401 simultanés → un seul refresh » | couvert | couvert | rechargement réel : E2E hors CI |
| AUTH-04 | `test_authenticate.py::test_get_me_lists_active_shops_sorted_by_name` ; `test_session_http.py::test_current_actor_hides_foreign_shops_and_needs_a_token` | couvert | couvert | |
| MEM-01 | `bt/application/shops/test_members.py::test_seller_needs_a_point_of_sale_and_gets_a_one_time_code` ; `test_shops_http.py::test_members_and_roles` | couvert | couvert | |
| MEM-02 | idem | couvert | couvert | |
| MEM-03 | `test_authenticate.py::test_actor_role_comes_from_the_membership_at_each_request` ; `R/test_isolation_http.py::test_role_is_read_per_shop_at_each_request` | couvert | couvert | |
| MEM-04 | `bt/application/identity/test_member_actions.py::test_reset_gives_a_non_simple_temporary_code_to_change_at_next_login` | couvert | couvert | |
| LOC-01 | `bt/application/shops/test_locations_and_modes.py::test_create_rename_and_unique_name` ; `test_shops_http.py::test_profile_settings_and_places` | couvert | couvert | |
| LOC-02 | `test_locations_and_modes.py::test_withdrawal_rules` ; `bt/application/stock/test_low_stock_and_probes.py::test_archive_and_location_deactivation_refused_with_stock` | couvert | couvert | code `LOCATION_HAS_STOCK` [Q-31] |
| LOC-03 | `test_locations_and_modes.py::test_withdrawal_rules` (`LastPointOfSale`) | couvert | couvert | |
| SET-01 | `bt/application/shops/test_settings_profile_access.py::test_settings_changes_are_journaled_and_bounded` ; `test_locations_and_modes.py::test_payment_modes` | couvert | couvert | |
| SET-02 | idem ; `test_shops_http.py::test_profile_settings_and_places` | couvert | couvert | |
| SET-03 | `test_locations_and_modes.py::test_payment_modes` ; `test_shops_http.py` (« Wave ») | couvert | couvert | écran Réglages non livré (E3) |
| PIN-01 | `bt/application/identity/test_change_pin.py::test_simple_codes_are_refused`, `test_first_login_change_clears_must_change_pin` | couvert | couvert | |
| PIN-02 | `bt/application/identity/test_change_pin_lockout.py` (6 tests) ; `bt/http/auth/test_change_pin_lock_http.py` | couvert | couvert | valeur selon § 15.1 : `422`, compteur séparé (et non `401`) |
| PIN-03 | `fs/features/auth/ChangePinPage.test.tsx` « refuse deux saisies différentes » | couvert | couvert | |
| PWA-01 | `fs/core/pwa/cachePolicy.test.ts`, `fs/core/pwa/updates.test.ts` | partiel | partiel | manifeste et page hors réseau : navigateur, hors CI |
| ALR-01 | `bt/http/journal/test_journal_http.py::test_each_user_sees_and_reads_only_their_alerts` ; `bt/contracts/test_alert_contract.py::test_round_trip_and_unread_count` | couvert | couvert | |
| ALR-02 | `fs/app/ShopShell.test.tsx` « la cloche ouvre les alertes (provisoire) » | hors CI | hors CI | écran Alertes non livré (E3) |
| ALR-03 | `test_journal_http.py::test_each_user_sees_and_reads_only_their_alerts` | couvert | couvert | |
| ALR-04 | `test_alert_contract.py::test_second_active_alert_with_same_key_is_a_duplicate` ; `test_alert_dispatcher_contract.py::test_low_stock_alerts_owner_and_accountant_only_once` | couvert | couvert | |
| CAT-01 | `bt/application/catalog/test_create_update.py::test_owner_creates_moto_with_price_and_history` ; `bt/domain/catalog/test_schema.py` | couvert | couvert | |
| CAT-02 | `test_create_update.py::test_duplicate_is_proposed_and_creation_idempotent` ; `bt/contracts/test_catalog_contract.py::test_brand_model_name_and_reference_unique_per_shop` | couvert | couvert | variante casse/accents : `test_schema.py::test_fold_…` |
| CAT-03 | `test_create_update.py::test_accountant_creates_without_selling_price` ; `bt/http/catalog/test_catalog_http.py::test_accountant_writes_without_prices` | couvert | couvert | |
| CAT-04 | `fs/shared/ui/AmountField.test.tsx`, `fs/features/sales/salesRules.test.ts` | partiel | partiel | règle « prix vide » de `saleChecks.ts` non vérifiée sur l'écran de vente |
| CAT-05 | `test_create_update.py::test_update_logs_changes_and_checks_version` | couvert | couvert | |
| CAT-06 | **`R/test_snapshots_http.py`** | manquant | couvert | nom figé sur la vente après renommage |
| CAT-07 | `test_create_update.py::test_update_logs_changes_and_checks_version` ; `test_catalog_http.py::test_patch_prices_archive_and_conflicts` | couvert | couvert | |
| CAT-08 | `bt/application/catalog/test_prices_archive_search.py::test_set_prices_owner_only_with_history` ; `R/test_snapshots_http.py` | couvert | couvert | |
| CAT-09 | **`R/test_snapshots_http.py`** | manquant | couvert | prix de base figé (780 000) après passage à 800 000 |
| CAT-10 | `test_prices_archive_search.py::test_set_prices_owner_only_with_history` ; `fs/features/catalog/ArticlePricesArchive.test.tsx` (`MIN_PRICE_ABOVE_BASE`) | couvert | couvert | |
| CAT-11 | `test_prices_archive_search.py::test_archive_and_reactivate` | couvert | couvert | |
| CAT-12 | idem ; `test_low_stock_and_probes.py::test_archive_and_location_deactivation_refused_with_stock` | couvert | couvert | |
| CAT-13 | `test_prices_archive_search.py::test_archive_and_reactivate` | couvert | couvert | |
| STK-01 | `bt/application/stock/test_reads.py::test_matrix_columns_filter_sort_and_badges` ; `bt/http/stock/test_stock_http.py::test_matrix_by_role_without_cost_leak` | couvert | couvert | |
| STK-02 | `test_stock_http.py::test_matrix_by_role_without_cost_leak` ; `R/test_no_leak_http.py` | couvert | couvert | |
| STK-03 | `fs/features/stock/StockMatrix.test.tsx` | couvert | couvert | |
| STK-04 | `StockMatrix.test.tsx` « recherche dès la 1re lettre, filtre par lieu, tri par quantité » | couvert | couvert | |
| STK-05 | `test_reads.py::test_history_hides_sale_documents_from_accountant` ; `test_stock_http.py::test_value_damaged_history_and_rights` | couvert | couvert | |
| INV-01 | `bt/application/stock/test_inventories.py::test_start_mask_count_resume_and_validate` ; `test_stock_http.py::test_inventory_flow_hides_theoretical_until_validation` | couvert | couvert | |
| INV-02 | `test_inventories.py::test_start_mask_count_resume_and_validate` | couvert | couvert | |
| INV-03 | idem ; `test_stock_http.py::test_inventory_flow_…` | couvert | couvert | |
| INV-04 | `test_inventories.py::test_start_mask_count_resume_and_validate` | couvert | couvert | |
| INV-05 | `test_inventories.py::test_one_open_inventory_per_location_and_abandon` | couvert | couvert | |
| INV-06 | `test_inventories.py::test_start_mask_count_resume_and_validate` | couvert | couvert | [Q-17] selon l'implémentation |
| ADJ-01 | `bt/application/stock/test_adjustments.py::test_adjustment_out_in_and_offcut` | couvert | couvert | |
| ADJ-02 | `test_adjustments.py::test_adjustment_rules_and_rights` ; `test_stock_http.py::test_adjustment_errors_and_idempotence` ; `bt/domain/test_quantity.py` | couvert | couvert | |
| ADJ-03 | `test_adjustments.py::test_idempotent_replay_and_alert_for_accountant_only` | couvert | couvert | |
| ADJ-04 | `test_adjustments.py::test_adjustment_rules_and_rights` | couvert | couvert | |
| ADJ-05 | `test_adjustments.py` ; `bt/domain/purchasing/test_replay_units.py::test_exits_and_neutral_entries_do_not_change_wac` | couvert | couvert | [Q-16] |
| LOW-01 | `test_low_stock_and_probes.py::test_low_stock_alerts_once_and_again_after_recovery` ; `test_alert_dispatcher_contract.py` | couvert | couvert | [Q-18] selon l'implémentation |
| LOW-02 | `test_low_stock_and_probes.py::test_shop_default_threshold_applies` | couvert | couvert | |
| VAL-01 | `test_reads.py::test_value_report_partial_and_separate_damaged` ; `test_stock_http.py::test_value_damaged_history_and_rights` | couvert | couvert | |
| VAL-02 | `test_stock_http.py::test_value_damaged_history_and_rights` ; `R/test_rights_matrix_http.py` (M08) | couvert | couvert | |
| PUR-01 | `bt/application/purchasing/test_record_purchase.py::test_default_reception_location_and_idempotence` ; `fs/features/purchasing/NewPurchase.test.tsx` | couvert | couvert | défaut = réglage, Garoua au Lot 1 (§ 15.1 Q-01) |
| PUR-02 | `test_record_purchase.py::test_pur02_price_gap_warning_over_thirty_percent` ; `fs/features/purchasing/NewPurchase.flows.test.tsx` | couvert | couvert | |
| PUR-03 | `NewPurchase.flows.test.tsx` « article introuvable : Créer l'article » | couvert | couvert | parcours navigateur : hors CI |
| PUR-04 | `test_record_purchase.py::test_rights_dates_and_input_errors` ; `bt/http/purchasing/test_purchasing_http.py::test_cross_shop_404_and_input_errors` | couvert | couvert | |
| PUR-05 | `bt/contracts/test_purchasing_contract.py::test_numbers_suppliers_unique_and_isolated` | couvert | couvert | |
| SUP-01 | `bt/application/purchasing/test_payments_suppliers.py::test_sup01_sup02_suppliers_and_sheet` | couvert | couvert | |
| SUP-02 | idem ; `R/test_journal_writes_http.py::test_no_business_delete_route` | couvert | couvert | |
| PUR-06 | `bt/application/purchasing/test_correct_cancel.py::test_pur06_correction_refused_below_what_left` | couvert | couvert | |
| PUR-07 | `test_correct_cancel.py::test_pur07_accountant_window_and_pur08_reason` | couvert | couvert | |
| PUR-08 | idem | couvert | couvert | |
| PUR-09 | `test_correct_cancel.py::test_pur09_cancel_reverses_entries_and_replays_wac` | couvert | couvert | |
| PUR-10 | `test_correct_cancel.py::test_pur10_cancel_refused_once_part_has_left` ; `test_purchasing_http.py::test_rights_seller_driver_and_cancel` | couvert | couvert | |
| PUR-11 | `test_payments_suppliers.py::test_pur11_list_filters_and_period_totals` | couvert | couvert | |
| PUR-12 | `test_payments_suppliers.py::test_pur12_payment_status_and_overpayment` | couvert | couvert | |
| SAL-01 | `bt/application/sales/test_record_sale.py::test_multi_payment_overpayment_and_incomplete_cash` | couvert | couvert | |
| SAL-02 | `fs/features/sales/NewSalePage.cash.test.tsx` « monnaie à rendre » | couvert | couvert | |
| SAL-03 | `bt/application/sales/test_stock_location_idempotence.py::test_seller_location_and_attribution` | couvert | couvert | |
| SAL-04 | `NewSalePage.cash.test.tsx` (dernier mode, quantité, stock du lieu) | couvert | couvert | |
| SAL-05 | `test_record_sale.py::test_multi_payment_overpayment_and_incomplete_cash` | couvert | couvert | |
| SAL-06 | `test_stock_location_idempotence.py::test_idempotent_replay_and_rights` ; `bt/http/sales/test_sales_http.py::test_rights_idempotence_and_cross_seller_404` | couvert | couvert | |
| SAL-07 | `test_record_sale.py::test_credit_customer_required_and_credit_limit` ; `test_sales_http.py::test_error_shapes_for_the_sale_screen` | couvert | couvert | |
| SAL-08 | `bt/application/receivables/test_legacy_write_off.py::test_change_responsible_terms_attachments_and_guarantor` | partiel | partiel | pièces jointes : identifiants seulement, aucune route d'envoi (E1) |
| RCP-01 | `bt/application/sales/test_reads_reports.py::test_receipt_duplicate_and_cancelled_mentions` ; `fs/features/sales/Receipt.test.tsx` | couvert | couvert | |
| RCP-02 | `test_sales_http.py::test_section_64_contract_and_no_cost_leak` ; `R/test_no_leak_http.py::test_owner_receipt_never_carries_a_cost` | couvert | couvert | |
| RCP-03 | `test_reads_reports.py::test_receipt_duplicate_and_cancelled_mentions` ; `Receipt.test.tsx` | couvert | couvert | |
| RCP-04 | `Receipt.test.tsx` « profils : 58 mm, 80 mm, A5 / A4 » | partiel | partiel | absence de débordement à l'impression : navigateur, hors CI |
| RCP-05 | — | manquant | manquant | « Partager » non livré (E2) |
| RCP-06 | — | hors CI | hors CI | terrain |
| SAL-09 | `test_reads_reports.py::test_own_scope_listing_search_and_rights` ; `fs/features/sales/SaleList.test.tsx` | couvert | couvert | |
| SAL-10 | `test_reads_reports.py::test_own_scope_listing_search_and_rights` ; `R/test_rights_matrix_http.py` (M13) | couvert | couvert | |
| SAL-11 | `test_reads_reports.py::test_own_scope_listing_search_and_rights` ; `R/test_isolation_http.py` (châssis de B) | couvert | couvert | |
| RPT-01 | `test_reads_reports.py::test_error_report_alert_and_reply` | couvert | couvert | |
| RPT-02 | idem ; `fs/features/sales/SaleDetail.test.tsx` | couvert | couvert | |
| MOD-01 | `bt/application/sales/test_modify_cancel.py::test_mod01_price_change_keeps_frozen_costs` ; `test_sale_link.py::test_mod01_price_change_revises_receivable` | couvert | couvert | |
| MOD-02 | `test_modify_cancel.py` ; `test_sales_http.py::test_owner_patch_and_customer_routes` | couvert | couvert | |
| MOD-03 | `test_modify_cancel.py::test_modify_details_payments_note_and_date` | partiel | partiel | [Q-06] ouverte |
| EXC-01 | `bt/application/sales/test_exchanges.py::test_exc01_only_the_difference_is_paid` ; `test_credit_exchanges.py` | couvert | couvert | échange à crédit (§ 15.1) |
| EXC-02 | `bt/application/sales/test_returns.py::test_scn05_partial_then_total_return` | couvert | couvert | code `RETURN_QUANTITY_EXCEEDED` |
| CUS-01 | `test_reads_reports.py::test_customers_scope_duplicates_and_sheet` | couvert | couvert | |
| CUS-02 | idem ; `R/test_isolation_http.py::test_uniqueness_and_numbering_are_per_shop` | couvert | couvert | |
| CUS-03 | `test_reads_reports.py::test_customers_scope_duplicates_and_sheet` ; `R/test_rights_matrix_http.py` (M22) | partiel | partiel | photo de pièce d'identité : E1 |
| REC-01 | `test_sale_link.py::test_scn01_credit_sale_opens_receivable_of_480000` | couvert | couvert | |
| REC-02 | `test_legacy_write_off.py::test_scn08_legacy_write_off_and_recovery` | couvert | couvert | |
| REC-03 | `bt/application/receivables/test_installments.py::test_rec03_default_to_oldest_receivable_and_explicit_choice` | couvert | couvert | |
| REC-04 | `bt/application/receivables/test_reminders_reads.py::test_rec04_rec05_summary_sort_and_filters` | couvert | couvert | |
| REC-05 | idem ; `bt/domain/receivables/test_receivable_domain.py::test_bands_q19` | couvert | couvert | |
| REC-06 | `test_reminders_reads.py::test_rec06_statement_running_balance` | couvert | couvert | |
| REM-01 | `test_reminders_reads.py::test_rem01_due_reminder_alerts_once_then_postpone` | couvert | couvert | |
| REM-02 | idem | couvert | couvert | |
| GUA-01 | `bt/http/receivables/test_receivables_http.py::test_legacy_write_off_follow_up_and_guarantor` | partiel | partiel | URL signée 60 s : E1 |
| EXP-01 | `bt/application/expenses/test_record_expense.py::test_fuel_expense_gets_first_number_and_cash_by_default` | couvert | couvert | |
| EXP-02 | `fs/features/expenses/NewExpense.test.tsx` « hors connexion : saisie conservée » | couvert | couvert | |
| EXP-03 | `bt/application/expenses/test_tags_categories.py::test_categories_base_locked_added_deactivable_owner_only` | couvert | couvert | |
| EXP-04 | `test_tags_categories.py::test_merge_retags_expenses_and_merges_totals` | couvert | couvert | |
| EXP-05 | `test_tags_categories.py::test_list_filters_period_and_pagination` ; `bt/http/expenses/test_expenses_http.py::test_list_totals_and_filters` | couvert | couvert | |
| EXP-06 | `bt/application/expenses/test_correct_cancel.py` (5 tests) | couvert | couvert | |
| EXP-07 | `test_tags_categories.py::test_repeat_gives_a_prefilled_draft_dated_today` ; `fs/features/expenses/ExpenseDetail.test.tsx` | couvert | couvert | |
| DSB-01 | `fs/features/dashboard/OwnerHome.test.tsx` | couvert | couvert | |
| DSB-02 | `bt/application/reporting/test_periods_and_indicators.py` ; `fs/features/dashboard/DashboardPeriods.test.tsx` | couvert | couvert | |
| DSB-03 | `OwnerHome.test.tsx` « Voir aussi au CMP » ; `bt/http/reporting/test_scn09_http.py` (écart 60 000) | couvert | couvert | |
| DSB-04 | `test_scn09_http.py::test_day_straddling_midnight` ; `fs/features/dashboard/DashboardDetails.test.tsx` | couvert | couvert | |
| DSB-05 | `bt/http/reporting/test_reporting_rights_http.py::test_homes_by_role_never_leak` ; `fs/features/dashboard/RoleHomes.test.tsx` | couvert | couvert | |
| DSB-06 | idem | couvert | couvert | |
| AUD-01 | `test_journal_http.py::test_owner_filters_by_user_period_and_entity` | partiel | partiel | phrase et écran Journal non livrés (E3) |
| AUD-02 | `bt/domain/audit/test_audit_values.py::test_sensitivity_rules` | couvert | couvert | |
| AUD-03 | `test_journal_http.py::test_owner_filters_by_user_period_and_entity` | couvert | couvert | |
| AUD-04 | idem ; `bt/application/audit/test_identity_events.py` | couvert | couvert | [Q-23] selon l'implémentation |
| AUD-05 | **`R/test_journal_writes_http.py::test_every_successful_write_is_journaled`** ; `bt/contracts/test_audit_recorder_contract.py` | partiel | couvert | avant : par cas d'utilisation, sans balayage |
| AUD-06 | **`R/test_journal_writes_http.py::test_no_business_delete_route`** | manquant | couvert | seule route `DELETE` : retrait de la délégation admin |
| AUD-07 | `test_record_expense.py`, `test_expenses_http.py` ; `bt/http/auth/test_login_http.py::test_device_header_is_mandatory_and_must_be_a_uuid7` | couvert | couvert | |
| MNY-01 | `bt/domain/test_money.py` ; `fs/shared/format/money.test.ts` | couvert | couvert | |
| CTR-STK-01 | `bt/application/stock/test_ledger.py::test_projection_equals_sum_of_movements` ; `bt/contracts/test_stock_ledger_contract.py` | couvert | couvert | mémoire + PostgreSQL |
| ATT-01 | — | manquant | manquant | E1 |
| AUD-08 | `bt/contracts/test_audit_contract.py::test_port_exposes_no_way_to_modify_or_delete` | partiel | partiel | refus des droits PostgreSQL : E5 |

### 5.2 Scénarios chiffrés (recette § 2)

| Cas | Test(s) | Avant | Après | Note |
| --- | --- | --- | --- | --- |
| SCN-01 | **`R/test_scn01_reference_http.py`** ; `test_record_purchase.py::test_scn01_twenty_motos_with_customs` ; `test_record_sale.py::test_scn01_credit_sale_of_780000_with_300000_deposit` ; `test_sales_http.py::test_section_64_contract_and_no_cost_leak` | partiel | couvert | avant : étape 7c (tableau de bord) non vérifiée |
| SCN-02 | `bt/domain/purchasing/test_costing.py::test_scn02_wac_and_rounding_rule`, `test_wac_stays_between_costs_without_exits` ; `test_record_purchase.py::test_scn02_wac_510000_and_stock_value` | couvert | couvert | |
| SCN-03 | `test_costing.py::test_scn03_prorata_and_remainder_to_heaviest_line` ; `fs/features/purchasing/costing.test.ts` | couvert | couvert | |
| SCN-04 | `test_correct_cancel.py::test_scn04_v1_…`, `test_scn04_v2_…`, `test_scn04_v3_replay_on_real_stock_gives_515000` ; `bt/contracts/test_purchasing_contract.py::test_costing_replay_on_ledger_gives_515000` | couvert | couvert | v3 = 515 000 (§ 15.1 Q-02) |
| SCN-05 | `bt/application/sales/test_returns.py` ; `bt/http/sales/test_sales_returns_http.py::test_returns_over_http` ; `bt/http/reporting/test_dashboard_flows_http.py` | couvert | couvert | |
| SCN-06 | `test_modify_cancel.py::test_scn06_cancel_restores_stock_and_counts_on_cancel_day` ; `test_sale_link.py::test_scn06_…` ; `R/test_numbering_chassis_http.py` | couvert | couvert | retrait le jour de l'annulation (§ 15.1 Q-09) |
| SCN-07 | `test_installments.py::test_scn07_installments_settle_then_cancel_reopens` ; `test_receivables_http.py::test_receivable_installments_receipt_and_rights` | couvert | couvert | |
| SCN-08 | `test_legacy_write_off.py::test_scn08_legacy_write_off_and_recovery`, `test_settled_receivable_cannot_be_written_off` | couvert | couvert | |
| SCN-09 | `bt/http/reporting/test_scn09_http.py` (2 tests) | couvert | couvert | |
| SCN-10 | `test_record_sale.py::test_unknown_cost_margin_not_computable_and_numbers_continue` ; `test_dashboard_flows_http.py` | couvert | couvert | |

### 5.3 Matrice des droits SEC-M (critère A10)

Avant T24, chaque ligne était vérifiée **par la `Policy`** (`bt/application/security/test_role_matrix.py::test_cell`, 2ᵉ saisie
indépendante du tableau du CDC) et, pour une partie des routes, par HTTP dans les suites de modules : **partiel**.
Après : **`R/test_rights_matrix_http.py::test_row_of_the_rights_matrix[Mnn]`** envoie chaque requête de la ligne pour les
4 rôles, avec un corps valide, sur une boutique neuve, et vérifie qu'**un 403 crée exactement une entrée « Accès
refusé »**. Les colonnes NM et ADM (404 partout) sont balayées par `R/test_isolation_http.py`. Les routes Lot 2
(`/transfers`, `/trucks`, `/drivers`, `/trips`, `/payroll`, `/imports`) répondent 404 (`test_lot_2_routes_do_not_exist_yet`).

| Ligne | Avant | Après | Note |
| --- | --- | --- | --- |
| M01 à M15, M17 à M28 | partiel | couvert | 27 lignes, une par test paramétré |
| M16 | partiel | couvert | vendeur sous le minimum : **201 + avertissement** (§ 15.1), `test_m16_seller_below_minimum_gets_a_warning_not_a_refusal` (E4) |
| M29 | couvert | couvert | `test_shops_http.py::test_platform_console` ; `R/…::test_m28_me_and_m29_platform_console` |
| M30 | couvert | couvert | `bt/http/sync/test_sync_disabled_http.py` ; ligne M30 de `R/` |

### 5.4 Non-fuite SEC-N (critère A4)

| Cas | Test(s) | Avant | Après | Note |
| --- | --- | --- | --- | --- |
| SEC-N01 | **`R/test_no_leak_http.py::test_no_forbidden_key_nor_sentinel_on_any_read_route[seller]`**, `test_seller_write_and_error_responses_carry_no_cost` ; suites `test_sales_http.py`, `test_catalog_http.py`, `test_stock_http.py`, `test_offline_snapshot_http.py` | partiel | couvert | toutes les routes de lecture + écriture + `STOCK_INSUFFICIENT`, `CREDIT_LIMIT_EXCEEDED`, `PRICE_BELOW_MINIMUM` ; sentinelles 543 210 et 234 567 |
| SEC-N02 | `R/…[accountant]` ; `test_stock_http.py` | partiel | couvert | sentinelle 777 777 ; exceptions E6 |
| SEC-N03 | `R/…[driver]` ; `test_reporting_rights_http.py::test_homes_by_role_never_leak` | partiel | couvert | 780 000, 543 210, 777 777 absents |
| SEC-N04 | `test_sales_http.py::test_section_64_contract_and_no_cost_leak` ; `R/…::test_owner_receipt_never_carries_a_cost` | couvert | couvert | |
| SEC-N05 | `fs/features/catalog/articleView.test.ts`, `fs/features/stock/stockView.test.ts`, `StockMatrix.test.tsx`, `SaleDetail.test.tsx`, `RoleHomes.test.tsx` (« vendeur : aucun coût… même si le serveur en envoyait ») | couvert | couvert | DOM jsdom ; navigateur réel hors CI |
| SEC-N06 | — | manquant | manquant | E1 |

### 5.5 Isolation SEC-I (critère A5)

| Cas | Test(s) | Avant | Après | Note |
| --- | --- | --- | --- | --- |
| SEC-I01 | **`R/test_isolation_http.py::test_shop_b_is_not_found_for_a_non_member_and_for_the_admin`** (toutes les routes) | partiel | couvert | avant : quelques routes par module |
| SEC-I02 | **`R/…::test_objects_of_b_are_not_found_through_shop_a`** | partiel | couvert | |
| SEC-I03 | **`R/…::test_references_to_objects_of_b_in_a_body_are_not_found`** | manquant | couvert | aucune écriture, stocks A et B inchangés |
| SEC-I04 | idem (client, mode, lieu de B) | manquant | couvert | |
| SEC-I05 | `R/…::test_objects_of_b_are_not_found_through_shop_a` (versions de B relues) ; `test_catalog_http.py::test_idempotent_creation_and_cross_shop_404` | partiel | couvert | |
| SEC-I06 | **`R/…::test_dashboard_counts_only_its_own_shop`** | manquant | couvert | |
| SEC-I07 | **`R/…::test_role_is_read_per_shop_at_each_request`** ; `test_authenticate.py::test_actor_role_comes_from_the_membership_at_each_request` | partiel | couvert | |
| SEC-I08 | `R/world.py` (même téléphone, même modèle, même châssis dans A et B) ; `bt/contracts/test_unique_contract.py::test_same_code_in_two_shops_is_allowed` | couvert | couvert | |
| SEC-I09 | `bt/contracts/test_numbering_contract.py::test_sequences_are_separate_per_shop` ; `R/…::test_uniqueness_and_numbering_are_per_shop` | couvert | couvert | |
| SEC-I10 | **`R/…::test_alerts_journal_and_chassis_search_stay_in_their_shop`** ; contrats alertes et journal | partiel | couvert | |
| SEC-I11 | `test_shops_http.py::test_admin_access_routes` ; `bt/application/security/test_admin_access.py` | couvert | couvert | |
| SEC-I12 | `bt/contracts/test_repository_contract.py::test_shop_b_never_reads_shop_a` et suivants (mémoire + PostgreSQL) | couvert | couvert | |
| SEC-I13 | **`bt/contracts/test_port_signatures.py`** | manquant | couvert | tous les ports et adaptateurs `ShopBoundPort` |
| SEC-I14 | — | manquant | manquant | E1 |

### 5.6 Blocage, révocation, désactivation (SEC-L, SEC-R, SEC-X)

| Cas | Test(s) | Avant | Après | Note |
| --- | --- | --- | --- | --- |
| SEC-L01 | `bt/application/identity/test_login.py::test_unknown_or_malformed_phone_gets_the_generic_message` ; `test_login_http.py::test_unknown_number_and_wrong_code_are_indistinguishable` | couvert | couvert | |
| SEC-L02 | `test_login.py::test_fifth_failure_locks_for_fifteen_minutes` ; `test_login_http.py::test_fifth_failure_then_423_with_until` | couvert | couvert | 423 avec l'heure de fin (§ 15.1) |
| SEC-L03 | idem ; `test_login.py::test_wrong_code_during_lock_is_also_423_and_not_counted` | couvert | couvert | |
| SEC-L04 | `test_login.py::test_fifth_failure_locks_for_fifteen_minutes` ; `bt/domain/identity/test_lockout.py` | couvert | couvert | |
| SEC-L05 | `test_login.py::test_failure_after_lock_expiry_restarts_the_counter` | couvert | couvert | |
| SEC-L06 | `test_login.py::test_success_between_failures_never_locks` | couvert | couvert | |
| SEC-L07 | `test_member_actions.py::test_owner_unlocks_a_locked_member` | couvert | couvert | |
| SEC-L08 | `test_login_http.py::test_unknown_number_and_wrong_code_are_indistinguishable` | couvert | couvert | |
| SEC-L09 | `bt/http/rate_limit/test_auth_rate_limit_http.py` (7 tests) | couvert | couvert | seuil retenu : 10 par IP [Q-41] |
| SEC-R01 | `test_member_actions.py::test_owner_revokes_every_device_and_the_member_can_log_in_again` | couvert | couvert | |
| SEC-R02 | `test_session_http.py::test_remote_revocation_applies_to_the_current_access_token` | couvert | couvert | |
| SEC-R03 | `bt/application/identity/test_refresh_logout.py` | couvert | couvert | |
| SEC-R04 | `test_member_actions.py::test_owner_revokes_every_device_and_the_member_can_log_in_again` | couvert | couvert | |
| SEC-R05 | `test_refresh_logout.py::test_reusing_a_rotated_token_revokes_only_that_session` | couvert | couvert | |
| SEC-R06 | `test_member_actions.py::test_seller_cannot_revoke_devices` | couvert | couvert | |
| SEC-X01 | `test_login.py::test_disabled_account_is_refused_only_after_a_correct_code` ; `test_login_http.py::test_disabled_account_gets_the_cdc_message` | couvert | couvert | |
| SEC-X02 | `test_authenticate.py::test_disabled_user_is_refused_on_every_request` ; `test_refresh_logout.py::test_disabled_account_cannot_refresh` | couvert | couvert | |
| SEC-X03 | — | partiel | partiel | ventes passées d'un vendeur désactivé non relues explicitement |
| SEC-X04 | `bt/domain/identity/test_user.py::test_disable_and_reactivate` ; `test_members.py` | couvert | couvert | |
| SEC-X05 | `test_members.py::test_role_change_and_last_owner_rule` ; `test_shops_http.py::test_members_and_roles` (`LAST_ACTIVE_OWNER`) | couvert | couvert | |
| SEC-X06 | `test_members.py::test_deactivation_is_per_shop` | couvert | couvert | rattachement seulement [Q-27] |

### 5.7 Erreurs par code (recette § 4)

| Cas | Test(s) | Avant | Après | Note |
| --- | --- | --- | --- | --- |
| ERR-STK-01 | `test_stock_location_idempotence.py::test_stock_insufficient_with_other_locations` ; `bt/application/stock/test_ledger.py::test_entries_exits_and_insufficient_stock_details` ; `R/test_numbering_chassis_http.py` (aucun numéro consommé) | couvert | couvert | |
| ERR-STK-02 | `test_stock_location_idempotence.py::test_stock_insufficient_with_other_locations` | couvert | couvert | |
| ERR-STK-03 | `test_ledger.py::test_entries_exits_and_insufficient_stock_details` | couvert | couvert | |
| ERR-STK-04 | `test_adjustments.py::test_adjustment_rules_and_rights` ; `test_stock_http.py::test_adjustment_errors_and_idempotence` | couvert | couvert | |
| ERR-STK-05 | `bt/infrastructure/postgres/test_stock_concurrency.py::test_two_exits_of_last_unit_one_wins` | couvert | couvert | PostgreSQL |
| ERR-PRM-01 | `bt/application/sales/test_min_price_rules.py::test_approval_required_seller_refused_owner_accepted` ; `bt/http/sales/test_sales_rules_http.py::test_owner_turns_approval_on` | couvert | couvert | 422 seulement si le réglage « accord » est actif (§ 15.1) |
| ERR-PRM-02 | `test_min_price_rules.py::test_approval_required_seller_refused_owner_accepted` | couvert | couvert | |
| ERR-PRM-03 | idem | couvert | couvert | |
| ERR-PRM-04 | `test_min_price_rules.py::test_default_setting_is_off`, `test_seller_below_minimum_is_accepted_with_a_warning` | couvert | couvert | |
| ERR-PRM-05 | `bt/application/sales/test_price_requests.py::test_request_accept_sell_then_single_use` ; `test_sales_returns_http.py::test_price_request_flow_over_http` | couvert | couvert | |
| ERR-PRM-06 | `test_price_requests.py::test_refused_and_decided_twice` | couvert | couvert | |
| ERR-PRM-07 | `test_price_requests.py::test_expiry_at_30_minutes_and_worker` | couvert | couvert | [Q-44] selon l'implémentation |
| ERR-PRM-08 | `test_price_requests.py::test_request_accept_sell_then_single_use`, `test_other_seller_other_article_and_owner_free` | couvert | couvert | |
| ERR-PRM-09 | `test_price_requests.py::test_expiry_at_30_minutes_and_worker` | couvert | couvert | |
| ERR-CRD-01 | `test_record_sale.py::test_credit_customer_required_and_credit_limit` ; `test_sale_link.py::test_credit_limit_uses_real_debt` | couvert | couvert | |
| ERR-CRD-02 | idem | couvert | couvert | |
| ERR-CRD-03 | `test_record_sale.py::test_quick_customer_is_merged_by_phone` ; `fs/features/sales/NewSalePage.credit.test.tsx` | couvert | couvert | |
| ERR-CRD-04 | `test_record_sale.py::test_credit_customer_required_and_credit_limit` | couvert | couvert | |
| ERR-OVR-01 | `test_receivables_http.py::test_receivable_installments_receipt_and_rights` | couvert | couvert | |
| ERR-OVR-02 | `test_record_sale.py::test_multi_payment_overpayment_and_incomplete_cash` ; `bt/domain/sales/test_sale_domain.py::test_payment_rules` | couvert | couvert | |
| ERR-OVR-03 | `test_record_sale.py::test_multi_payment_overpayment_and_incomplete_cash` | couvert | couvert | |
| ERR-OVR-04 | `test_installments.py::test_scn07_installments_settle_then_cancel_reopens` | couvert | couvert | |
| ERR-OVR-05 | `test_payments_suppliers.py::test_pur12_payment_status_and_overpayment` | couvert | couvert | |
| ERR-DAT-01 | **`R/test_dates_http.py::test_seller_window_and_owner_without_past_limit`** ; `bt/domain/test_business_day.py::test_other_roles_go_back_seven_days_at_most` | partiel | couvert | avant : règle de domaine, dépenses et achats ; pas la vente |
| ERR-DAT-02 | idem (`details.min_date`) | partiel | couvert | |
| ERR-DAT-03 | idem | partiel | couvert | |
| ERR-DAT-04 | idem ; `test_business_day.py::test_owner_has_unlimited_past` | partiel | couvert | |
| ERR-DAT-05 | `test_record_expense.py::test_entry_date_window_rg_t09` ; `test_record_purchase.py::test_rights_dates_and_input_errors` | couvert | couvert | |
| ERR-DAT-06 | `test_receivable_domain.py::test_reminder_transitions` ; `test_receivables_http.py::test_legacy_write_off_follow_up_and_guarantor` | couvert | couvert | [Q-47] |
| ERR-DAT-07 | **`R/test_dates_http.py::test_the_business_day_is_the_one_of_douala`** ; `test_business_day.py::test_business_date` | partiel | couvert | |
| ERR-DAT-08 | idem | partiel | couvert | |
| ERR-DAT-09 | **`R/test_dates_http.py::test_device_capture_time_at_most_ten_minutes_ahead`** ; `test_record_expense.py::test_device_time_is_kept_unless_far_in_the_future` | partiel | couvert | 11 min refusé, 9 min accepté (§ 15.1 Q8) |
| ERR-DUP-01 | `test_stock_location_idempotence.py::test_chassis_unique_among_valid_sales` ; `test_sales_http.py::test_error_shapes_for_the_sale_screen` ; `R/test_numbering_chassis_http.py` | couvert | couvert | |
| ERR-DUP-02 | `bt/contracts/test_sales_contract.py::test_chassis_claims_reports_and_prints` ; **`R/test_numbering_chassis_http.py::test_a_sold_chassis_cannot_be_sold_again_in_any_spelling`** | couvert | couvert | normalisation : casse, espaces, ponctuation [Q-33] |
| ERR-DUP-03 | `test_chassis_unique_among_valid_sales` ; `R/…::test_same_chassis_twice_in_one_sale_and_scope_of_uniqueness` | couvert | couvert | |
| ERR-DUP-04 | `test_reads_reports.py::test_customers_scope_duplicates_and_sheet` | couvert | couvert | |
| ERR-DUP-05 | `test_members.py::test_existing_account_is_attached_and_double_membership_is_409` | couvert | couvert | |
| ERR-DUP-06 | `test_catalog_http.py` ; `test_payments_suppliers.py` ; `test_locations_and_modes.py::test_create_rename_and_unique_name` | couvert | couvert | |
| ERR-VER-01 | `test_catalog_http.py::test_patch_prices_archive_and_conflicts` | couvert | couvert | |
| ERR-VER-02 | `bt/application/receivables/test_retry.py::test_retries_races_then_gives_up` | partiel | partiel | course « modification de vente + versement » non rejouée en réel |
| ERR-VER-03 | **`bt/infrastructure/postgres/test_sales_numbering.py`** ; `test_concurrency.py::test_20_concurrent_sales_get_continuous_gapless_numbers` | partiel | couvert | |
| ERR-FEA-01 | `test_sync_disabled_http.py::test_v1_shop_refuses_sync_and_snapshot_for_every_role` | couvert | couvert | |
| ERR-FEA-02 | idem | couvert | couvert | |
| ERR-FEA-03 | idem | couvert | couvert | |
| ERR-FEA-04 | `test_sync_disabled_http.py::test_admin_override_opens_one_shop_only_then_closes_it` | couvert | couvert | |
| ERR-MSC-01 | `test_sales_http.py`, `test_receivables_http.py`, `R/test_rights_matrix_http.py` (`INVALID_STATE_TRANSITION`) | couvert | couvert | |
| ERR-MSC-02 | `bt/http/test_errors.py::test_request_validation_gives_400_with_fields` | couvert | couvert | |
| ERR-MSC-03 | `test_session_http.py::test_current_actor_hides_foreign_shops_and_needs_a_token` | couvert | couvert | |
| ERR-MSC-04 | `test_errors.py::test_unexpected_error_gives_500_without_leak_and_is_logged` | couvert | couvert | |

### 5.8 Hors-ligne (droit activé en configuration de test)

| Cas | Test(s) | Avant | Après | Note |
| --- | --- | --- | --- | --- |
| OFF-01 | `fs/features/sales/NewSalePage.offline.test.tsx` « coupure : Connexion nécessaire, aucune file, aucun appel à /sync » | couvert | couvert | |
| OFF-02 | `fs/features/dashboard/OwnerHome.test.tsx` « jamais de chiffre en cache » ; `test_sync_disabled_http.py` | couvert | couvert | |
| OFF-03 | `fs/core/offline/offlineGateways.test.ts` | couvert | couvert | |
| OFF-04 | `NewSalePage.offline.test.tsx` « vente hors ligne → reçu provisoire → numéro définitif » ; `test_sync_operations_http.py` | couvert | couvert | |
| OFF-05 | `test_sync_operations_http.py::test_same_op_id_twice_is_a_duplicate_and_one_sale` | couvert | couvert | |
| OFF-06 | `test_ledger.py::test_deferred_exit_marks_stock_to_verify_and_alerts` ; `test_sync_operations_http.py::test_deferred_sale_below_zero_is_accepted_with_stock_to_verify` | couvert | couvert | |
| OFF-07 | `test_sync_operations_http.py::test_refused_operation_does_not_block_the_next_ones` ; `fs/app/OfflineQueue.test.tsx` | couvert | couvert | |
| OFF-08 | `OfflineQueue.test.tsx` « déconnexion : bloquée, puis double confirmation » ; `fs/core/offline/capture.test.ts` | couvert | couvert | |
| OFF-09 | `test_sync_operations_http.py::test_offline_expense_and_refused_operation_kinds` | couvert | couvert | |
| OFF-10 | `fs/core/offline/db.test.ts` « la migration 1 → 2 garde la file » | couvert | couvert | activation réelle du service worker : hors CI |

### 5.9 Parcours E2E, accessibilité, performance

| Cas | Équivalent unitaire existant | Avant | Après | Note |
| --- | --- | --- | --- | --- |
| E2E-01 à E2E-10 | voir A1, A6, SCN-01 ; `NewSalePage.*.test.tsx`, `NewInstallment.test.tsx`, `OwnerHome.test.tsx`, `SaleDetail.test.tsx`, `LoginPage.test.tsx`, `ChangePinPage.test.tsx`, `routes.test.tsx`, `NewPurchase.test.tsx` | hors CI | hors CI | 10 parcours, exclus par décision ; dossier `e2e/` présent mais non exécuté |
| A11Y-01 | `fs/app/dev/UiShowcase.a11y.test.tsx` ; axe dans `LoginPage`, `ChangePinPage`, `OwnerHome` | partiel | partiel | axe en jsdom : contrastes et mise en page non calculés |
| A11Y-02 | `fs/shared/ui/Button.test.tsx` (48 / 56 px), `Navigation.test.tsx`, `QuantityStepper.test.tsx` | partiel | partiel | tailles des jetons, pas des boîtes rendues |
| A11Y-03 | — | hors CI | hors CI | taille calculée : navigateur |
| A11Y-04 | `Button.test.tsx` « anneau de focus visible » ; `ConfirmDialog.test.tsx` (piège du focus) | partiel | partiel | |
| A11Y-05 | `fs/shared/ui/Field.test.tsx` (libellé relié, `aria-live`) | partiel | partiel | |
| A11Y-06 | — | hors CI | hors CI | zoom 200 % |
| A11Y-07 | `fs/shared/ui/Feedback.test.tsx` (pastille sans mot refusée) | partiel | partiel | contrastes : navigateur |
| PERF-01 | `npm run size` (size-limit, job CI `frontend`) | couvert | couvert | |
| PERF-02 | idem (JS initial mesuré sur le fichier d'entrée) | couvert | couvert | |
| PERF-03 | — | manquant | manquant | module PDF non livré (E2) |
| PERF-04 | — | hors CI | hors CI | Lighthouse |
| PERF-05 | `NewSalePage.cash.test.tsx` « recherche dès la première lettre » | hors CI | hors CI | chronométrage navigateur |
| PERF-06 | `bt/infrastructure/postgres/test_reporting_indexes.py::test_every_dashboard_aggregate_uses_an_index` | partiel | partiel | plan d'exécution indexé ; p95 < 300 ms non mesuré |

## 6. Tests ajoutés par T24

| Fichier | Tests | Ce qu'il prouve |
| --- | --- | --- |
| `R/conftest.py`, `R/world.py`, `R/paths.py`, `R/routes.py`, `R/routes_trade.py`, `R/matrix.py` | — | banc : application complète (mémoire ou PostgreSQL), boutiques A et B, table de **toutes** les routes de boutique avec un corps valide, matrice § 4.2 |
| `R/test_rights_matrix_http.py` | 37 | SEC-M01 à M30 × 4 rôles ; 1 entrée « Accès refusé » par 403 ; routes Lot 2 absentes |
| `R/test_no_leak_http.py` | 7 | SEC-N01 à N04 sur toutes les routes ; garde-fou OpenAPI ↔ table des routes |
| `R/test_isolation_http.py` | 7 | SEC-I01 à I10 (NM et ADM : 404 partout) |
| `R/test_numbering_chassis_http.py` | 7 | RG-T05 (refus sans numéro, annulé gardé, séquences par type et boutique), RG-M01 (5 graphies, même vente, A/B, libération) |
| `R/test_scn01_reference_http.py` | 1 | critère A2 de bout en bout |
| `R/test_journal_writes_http.py` | 2 | critère A7 : chaque écriture réussie journalisée ; aucune route `DELETE` métier |
| `R/test_snapshots_http.py` | 1 | CAT-06, CAT-09 |
| `R/test_dates_http.py` | 3 | ERR-DAT-01 à 04, 07 à 09 sur la vente |
| `bt/contracts/test_port_signatures.py` | 3 | SEC-I13 |
| `bt/infrastructure/postgres/test_sales_numbering.py` | 1 | critère A8 par 20 `RecordSale` concurrents |

Commandes : `uv run pytest tests/http/recette` (mémoire) ; `uv run pytest tests/http/recette tests/infrastructure/postgres
--backend=postgres` (PostgreSQL, `TEST_DATABASE_URL`).
