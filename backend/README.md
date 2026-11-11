# Backend — Gestion de boutiques

FastAPI + Python 3.12, Clean Architecture (voir `../specs.md` § 4). Gestionnaire : [uv](https://docs.astral.sh/uv/).

## Démarrer

```bash
uv sync                          # crée .venv et installe les versions verrouillées (uv.lock)
cp .env.example .env             # puis ajuster ; ENVIRONMENT est obligatoire
uv run uvicorn app.bootstrap.container:build_app --factory --reload
curl http://127.0.0.1:8000/api/v1/health   # {"status":"ok"}
```

Une configuration manquante ou invalide arrête le démarrage (`ConfigurationError`).

## Vérifications (toutes bloquantes en CI)

```bash
uv run ruff check .                     # lint
uv run ruff format --check .            # format
uv run mypy                             # typage strict (app, tests, tools)
uv run lint-imports                     # règle de dépendance entre couches
uv run pytest --cov                     # tests + couverture (seuil 90 %), sans base
uv run python tools/check_file_length.py   # aucun .py > 200 lignes dans app/ et tests/
```

Windows, sortie redirigée (CI, `> fichier`) : exporter `PYTHONUTF8=1`, sinon `lint-imports`
(via `rich`) plante en encodant ses symboles en cp1252.

## Persistance (PostgreSQL, migrations)

`PERSISTENCE_BACKEND=memory|postgres` choisit l'adaptateur (`app/bootstrap/persistence.py`) ;
absent, il vaut `memory` si `ENVIRONMENT=test`, `postgres` sinon. `postgres` exige
`DATABASE_URL` ; `memory` est refusé en prod. Base locale : `../infra/README.md`.

```bash
docker compose -f ../infra/docker-compose.dev.yml up -d --wait postgres   # depuis backend/

# Migrations (Alembic, dossier alembic/) — ne lisent que DATABASE_URL (env ou .env)
uv run alembic upgrade head
uv run alembic check                     # le schéma déclaré (tables.py) = les migrations
uv run alembic revision -m "catalogue"   # une migration par changement, jamais éditée après fusion

# Contrats + concurrence sur PostgreSQL (base de test vidée à chaque test, migrée au démarrage)
export TEST_DATABASE_URL=postgresql+psycopg://boutique:boutique-dev-password@127.0.0.1:5432/boutique_test
uv run pytest tests/contracts tests/infrastructure/postgres --backend=postgres
```

- Sans option, `pytest` tourne **sans base** : contrats sur l'adaptateur mémoire, et adaptateur
  SQL rejoué sur SQLite (`tests/infrastructure/sqlalchemy`). Les tests de
  `tests/infrastructure/postgres` sont alors sautés avec leur motif (`-ra`).
- `--backend=postgres` sans `TEST_DATABASE_URL`, base injoignable ou base dont le nom ne contient
  pas « test » : la session **échoue** (`UsageError`), elle ne saute rien.
- Tables métier : les déclarer dans `app/infrastructure/persistence/sqlalchemy/tables.py`
  (contraintes `UNIQUE (shop_id, …)` nommées comme les `UniqueKey` du port) + migration.

## Journal, alertes, droits d'offre (T09)

- **Journal** (`app/domain/audit`, port `AuditLog`) : en ajout seul, écrit par le handler
  `AuditRecorder` dans la transaction de l'action. Tout événement de domaine hérite
  d'`AuditableEvent` (`audit_record()`) ou de `NotAudited` ; sinon `UnauditedEvent` annule la
  transaction. Les refus d'accès sont inscrits par le gestionnaire d'erreurs HTTP
  (`RecordAccessDenied`).
- **Alertes** (`app/domain/alerts`, `AlertDispatcher`) : un module branche ses règles par
  `app.state.journal.alerts.register(TypeDEvénement, règle)` ; `dedup_key` = « une seule fois ».
- **Droits d'offre** : `require_entitlement(entitlements, shop_id, Entitlement.OFFLINE_CAPTURE)`
  lève `403 FEATURE_DISABLED` (offre gratuite : faux, sauf surcharge de l'administrateur).
- Nouveau port lié à la boutique sans agrégat : hériter de `ShopBoundPort`, adaptateurs
  `MemoryShopStore` / `SqlShopStore`, inscrits dans `MEMORY_REPOSITORIES` / `SQL_REPOSITORIES`.

## Boutiques, membres, console plateforme (T10)

- **Profils** (`app/domain/profiles`) : Motos et camions (complet), Prêt-à-porter et Textile
  (minimaux, Lot 3) ; `profile_for(code)` (inconnu → 400 `UNKNOWN_PROFILE`). Menus ≤ 5 entrées
  vérifiés à l'import. Exposés par `GET /shops/{id}/profile`.
- **Ouvrir une boutique** (admin plateforme) : `POST /api/v1/platform/shops`
  `{profile_code, name, city, phone, owner: {name, phone}}` → 201, code provisoire du
  propriétaire renvoyé **une fois** (`null` si le téléphone existait : compte rattaché). Lieux,
  réglages, modes de paiement, catégories et rattachement « Propriétaire » viennent du profil.
  `PATCH /platform/shops/{id}` : `modules`, `status`, `entitlements` (`offline_capture`).
- **Transaction commune** : l'unité plateforme (`IdentityUnitOfWork`) joint des unités de
  boutique (`join_shop`) sur **la même transaction** (SQL : une connexion ; mémoire : validation
  commune sous verrou). Les événements de l'identité sont journalisés ainsi dans chaque boutique.
- **Désactivation** (RG-D06) : par rattachement (`PATCH /members/{uid}` `active`) ; sans aucun
  rattachement utilisable, connexion et rafraîchissement → 403 `ACCOUNT_DISABLED`. Débloquer,
  redonner un code, déconnecter les appareils agissent sur le compte entier.
- **Délégation** : `POST/GET/DELETE /shops/{id}/admin-access` (24 h, lecture seule, chaque accès
  de l'admin journalisé).
- **Identité sur PostgreSQL** : `app_user`, `device_session`, `merchant_account` (migration 0003).
- **Démonstration** (dev seulement, refusée en prod) : après `alembic upgrade head`,
  `uv run python -m tools.seed_dev` ouvre « Motos Garoua » (admin, propriétaire, vendeur,
  comptable, chauffeur ; codes affichés). Relancer ne recrée rien.

## Catalogue (T13)

- **Routes** (`/shops/{id}/…`) : `GET/POST /articles` (`?q=&status=active|archived|all&sort=&cursor=&limit=`),
  `GET/PATCH /articles/{aid}`, `PUT /articles/{aid}/prices`, `POST /articles/{aid}/archive|reactivate`.
  Création idempotente par `id` client (201 puis 200).
- **Champs du profil** dans `fields` (codes de `GET /profile`), validés par le domaine
  (`domain/catalog/schema.py`) ; non promus → colonne JSON `attributes`. Nom affiché « Marque
  Modèle » (motos) ou saisi. Unicité par boutique sur clés **pliées** (casse, accents, espaces,
  ponctuation ignorés) : marque + modèle, référence. Doublon → 409 `DUPLICATE` +
  `details.existing_id`. Référence vide (prêt-à-porter, textile) → `REF-000001` (compteur par boutique).
- **Recherche** portable : sous-chaîne dans `search_key` (pliée par le domaine), ordre et curseur
  sur `(sort_key, id)`. Tri « plus vendus » : port `SalesRanking` (T16), sinon 400 `SORT_UNAVAILABLE`.
- **Prix** (propriétaire, `PRICE_SET`) : historique `price_history` ; minimum ≤ base ; minimum
  refusé si le réglage est inactif (`MIN_PRICE_DISABLED`). **Visibilité** :
  `application/catalog/visibility.py` (seul endroit) — vendeur sans `last_cost`/`wac` (clés
  absentes), comptable sans prix de vente, chauffeur 403.
- `last_cost`/`wac` écrits par `Article.record_costs`, réservé aux Achats (T15). Archivage :
  port `ArticleStock`, servi par le module Stock (T14).

## Dépenses (T18)

- Routes sous `/shops/{id}` : `GET/POST /expenses` (filtres `from`, `to`, `category_id`,
  `tag_id`, `location_id`, `user_id`, `payment_mode_id`, curseur ; totaux et répartition par
  catégorie hors annulées), `GET/PATCH /expenses/{eid}`, `POST /expenses/{eid}/cancel
  {reason}`, `GET /expenses/{eid}/repeat` (brouillon, rien n'est écrit),
  `GET/POST/PATCH /expense-categories`, `GET /tags?search=`, `POST /tags/merge`.
- Numéro `D-000001` attribué à la création ; `id` client idempotent ; `X-Captured-At` gardé.
- Délai de l'auteur (comptable, ses dépenses) : jusqu'à minuit **Douala** le jour de
  `received_at` (`CORRECTION_WINDOW_CLOSED`, 422) ; le propriétaire corrige toujours.
- Tags : unicité sans casse par `name_key` calculée en Python (NFC + `casefold`) ; une fusion
  **réécrit** les dépenses du tag source et aplatit les fusions antérieures.
- « Autre » exige une description : `expense_category.requires_description` (migration
  `0004_expenses`, qui le pose sur les « Autre » existants).

## Stock (T14)

- **Grand livre** : `application/stock/ledger.py` (`StockLedger`) est le **seul** point d'entrée
  des mouvements (`record_entry`, `record_exit(deferred=…)`, `reverse`), appelé dans la
  transaction du document source ; il met à jour la projection `stock_level` (verrou
  optimiste) et refuse en ligne un stock négatif (`422 STOCK_INSUFFICIENT`, `details.available`
  et `other_locations`). Différé (RG-T18) : accepté, `stock_to_verify`, alerte. Sur conflit de
  concurrence, rejouer la transaction par `with_stock_retry` (`retry.py`, 3 essais).
- **Routes** (`/shops/{id}/…`) : `GET /stock?q=&location_id=&sort=name|quantity_asc|quantity_desc`,
  `GET /stock/value`, `GET /stock/damaged`, `GET /articles/{aid}/movements`, `POST /adjustments`,
  `POST /inventories`, `GET /inventories/{iid}`, `PUT /inventories/{iid}/counts`,
  `POST /inventories/{iid}/validate|abandon`. Visibilité : `application/stock/visibility.py`.
- **Décisions** : seuil bas **strict** et stock vendable tous lieux (Q-18) ; théorique d'inventaire
  lu à la validation, jamais renvoyé avant (Q-17) ; ajustement + au CMP courant (Q-16) ;
  `other_locations` = lieux actifs à stock > 0 (Q-43) ; valeur sans coût = `null` + nombre
  d'articles sans coût (RG-T15). Alertes : `application/stock/alerts.py`, branchées dans
  `bootstrap/core.py`.
- **Migration** `0006_stock` ; seed de dev : stock de départ des six motos (`tools/seed_stock.py`).

## Achats et Costing (T15)

- **Routes** (`/shops/{id}/…`) : `GET/POST /suppliers`, `GET /suppliers/{sid}?from=&to=`
  (fiche, total acheté), `PATCH /suppliers/{sid}` (`active: false` pour désactiver ; aucun
  `DELETE`), `GET/POST /purchases` (`?from=&to=&supplier_id=&article_id=&location_id=&cursor=&limit=`,
  défaut : mois en cours, totaux hors annulés), `GET/PATCH /purchases/{pid}` (`version` +
  `reason`), `POST /purchases/{pid}/cancel {reason}` (propriétaire), `POST /purchases/{pid}/payments`.
  Créations idempotentes par `id` client (201 puis 200). Vendeur et chauffeur : 403.
- **Costing** (`domain/purchasing/costing.py`, `replay.py`) : frais au prorata par
  `Money.allocate` (somme exacte) ; coût unitaire final **par unité de stock** (yards et pièces
  convertis en mètres, `units.py`). **Arrondi** : fractions exactes, puis franc le plus proche,
  demi vers le haut (total de ligne, coût unitaire, CMP).
- **Rejeu** (`application/purchasing/costs.py`) : après chaque achat, correction ou annulation,
  tous les mouvements de l'article (`StockMovementLog.chronology`) sont rejoués par date
  d'opération, paires « mouvement + Annulation » retirées, CMP pondéré par le **stock réel**
  (Q-02 : 515 000 dans SCN-04 v3) ; dernier coût = entrée coûtée la plus récente (égalité :
  ordre d'enregistrement). Écrit par `Article.record_costs` dans la même transaction.
- **Entrées de stock** : « Entrée achat » datée du jour d'achat (`entry_instant`) ; correction =
  nouvelles entrées puis annulation des anciennes ; refus `STOCK_ALREADY_LEFT` si la quantité
  gardée est sous la part déjà sortie du lieu (plus bas solde depuis l'entrée).
- **Erreurs** : `PRICE_GAP_CONFIRMATION_REQUIRED` (> 30 % du dernier coût, `confirm_price_gap`),
  `CORRECTION_WINDOW_CLOSED` (comptable après J+7), `OVERPAYMENT`, `REASON_REQUIRED`.
- **Pour T16** : figer `article.last_cost` / `article.wac` lus dans la transaction de la vente ;
  une correction d'achat ne réécrit jamais une vente.
- **Migration** `0007_purchasing`.

## Ventes (T16a)

- **Routes** (`/shops/{id}/…`) : `GET/POST /sales` (`?from=&to=&seller_id=&article_id=&payment_mode_id=&kind=&q=&cursor=&limit=`,
  défaut : le jour ; `q` = numéro définitif/provisoire ou châssis, toutes dates sans période),
  `GET/PATCH /sales/{sid}` (`version` + `reason`, propriétaire), `POST /sales/{sid}/cancel
  {reason, refund_payments}`, `POST /sales/{sid}/error-reports`, `POST /error-reports/{rid}/reply`,
  `GET /sales/{sid}/receipt` (DTO, chaque appel = une impression), `GET/POST /customers?q=`,
  `GET/PATCH /customers/{cid}`. Créations idempotentes par `id` client (201 puis 200, même si
  le contenu rejoué diffère, Q-37). Comptable et chauffeur : 403.
- **Visibilité** : `application/sales/views.py` (`show_costs`) — vendeur sans `frozen_last_cost`,
  `frozen_wac`, `margin`, `margin_wac` (clés absentes), propriétaire avec ; reçu sans aucun coût
  (réglage d'impression `margin_mm` exposé en `padding_mm`). Portée OWN du vendeur dans les
  requêtes (`seller=`), clients « à lui » = créés par lui ou ayant une vente de lui.
- **Règles tranchées** : comptant payé en entier (`PAYMENT_INCOMPLETE`, Q-12) ; crédit : client
  obligatoire, acompte < total ; payé ≤ total (`OVERPAYMENT`) ; plafond strict (vendeur
  `CREDIT_LIMIT_EXCEEDED`, propriétaire avertissement `warnings`) ; vendeur sous le minimum
  `PRICE_BELOW_MINIMUM` (`request_required` ; débloqué par une demande acceptée, T16b) ;
  vendeur limité à son lieu habituel (`LOCATION_NOT_ALLOWED`, Q-36) ; total de ligne et coût =
  arrondi au franc demi vers le haut (T04) ; châssis normalisé (lettres et chiffres en
  majuscules) unique parmi les ventes valides via `sold_chassis.active_key` ; duplicata dès la
  2ᵉ impression ; totaux de liste = ventes de la période − ventes annulées pendant (Q-09) ;
  « plus vendus » = quantités des 30 derniers jours hors annulées.
- **Créances (T17)** : événements `CreditSaleRecorded`, `CreditSaleAmountsChanged`,
  `CreditSaleCancelled` (`domain/sales/receivable_events.py`) consommés par `ReceivableSync` ;
  port `CustomerDebt` servi par `ReceivableCustomerDebt` ; `receivable.id` = id de la vente.
- **Migration** `0008_sales`.

## Ventes — demandes de prix et retours (T16b)

- **Routes** (`/shops/{id}/…`) : `POST/GET /price-requests` (vendeur : crée, lit les siennes ;
  propriétaire : liste celles en attente), `GET /price-requests/{rid}`,
  `POST /price-requests/{rid}/decision {decision: accept|refuse, version?}` (propriétaire),
  `POST /sales/{sid}/returns` (propriétaire ; retour simple ou `exchange`), `GET
  /sales/{sid}/returns` (retours + `balances` : vendu / rendu / rendable par ligne ; vendeur sur
  ses ventes, sans coût ni marge). Créations idempotentes par `id` client. Comptable : 403.
- **Demande de prix (Q-44 tranchée)** : expire 30 min après la demande (à 30:00 pile :
  expirée) ; acceptée, elle vaut 30 min **dès l'accord** ; usage unique (liée à la vente) ;
  couvre les lignes de **son article** dont le prix est **≥ prix accordé**, pour **son vendeur**.
  Sinon `PRICE_BELOW_MINIMUM` + `details.price_request` (`not_found`, `other_seller`,
  `other_article`, `pending`, `refused`, `expired`, `used`, `price_too_low`). Statut lu
  **effectif** à l'horloge ; `SalesModule.expire_price_requests.execute(shop_id, now)` l'inscrit
  (worker TR-19, idempotent). Alerte « Demande de prix » aux propriétaires
  (`price_request:<id>`), résolue à la décision / expiration ; le nom du vendeur n'est pas dans
  le message (l'alerte ouvre la demande, qui porte `seller_id`).
- **Retour (Q-05 tranché)** : montant et marge aux **coûts figés** de la ligne, comptés **le
  jour du retour** (`returned_on`) ; dernier retour d'une ligne = reste exact (pas d'écart
  d'arrondi). Crédit : la valeur rendue baisse d'abord la créance (`credit_reduction` =
  min(valeur, reste de la vente non encore baissé), événement `CreditSaleReturned(sale_id,
  amount)`) ; remboursement ≤ valeur − baisse et ≤ payé − remboursements précédents
  (`OVERPAYMENT`). Quantité > rendable : `RETURN_QUANTITY_EXCEEDED` (422, Q-31). Châssis
  rendus à préciser sur une ligne partielle, puis libérés. Une vente avec retour ne se modifie
  ni ne s'annule plus (`INVALID_STATE_TRANSITION`). Vente annulée : retour refusé (idem).
- **Échange** : retour d'abord (stock, châssis), puis nouvelle vente par `RecordSale.record_in`
  (mêmes règles, lieu d'origine par défaut). L'avoir (valeur − baisse de créance) est remboursé
  dans `exchange.mode_id` **et** versé à la nouvelle vente dans ce mode (plafonné à son total) :
  le client ne paie que la différence (`exchange.sale.payments`) ou la reçoit.
- **Pour T19** : `SaleReturnRepository.between(jour, jour)` → `amount`, `margin`, `margin_wac`,
  `refund` (montant, mode, `refunded_on`), `credit_reduction`, `returned_on`.
- **Points ouverts** : la baisse de créance est calculée sur le reste **à la vente** (sans les
  versements T17 : T17 la plafonne au dû réel) ; « payé » = payé à la vente.
- **Migration** `0010_sales_returns` (sur `0008_sales`, parallèle à `0009_receivables`).

## Créances et versements (T17)

- **Routes** (`/shops/{id}/…`) : `GET /receivables?status=&seller_id=&band=under_30|31_60|61_90|over_90&reminder_overdue=&quiet=`
  (en tête : total à recevoir, clients débiteurs, versements du jour ; tri par reste décroissant,
  sans pagination), `POST /receivables` (créance ancienne, propriétaire), `GET/PATCH /receivables/{rid}`
  (`version` ; `responsible_seller_id` : propriétaire seul), `POST /receivables/{rid}/installments`,
  `POST /customers/{cid}/installments` (plus ancienne créance du client ayant un reste, REC-03),
  `POST /installments/{iid}/cancel {reason}`, `GET /installments/{iid}/receipt`,
  `POST /receivables/{rid}/write-off {reason}`, `POST /receivables/{rid}/reminders`,
  `PATCH /reminders/{mid}`, `POST /receivables/{rid}/guarantors`, `GET /customers/{cid}/statement`.
  Créations idempotentes par `id` client (201 puis 200). Comptable et chauffeur : 403.
- **Vente liée** : handler `ReceivableSync` (premier handler de l'unité de boutique,
  `bootstrap/core.py`) — `CreditSaleRecorded` ouvre la créance **dans la transaction de la vente**
  (un échec annule la vente) ; elle porte l'**identifiant de la vente** (`receivable.id` de la
  réponse de vente) ; `CreditSaleAmountsChanged` → nouveau montant initial (`AMOUNT_BELOW_PAID`
  422 s'il passait sous le déjà versé : la modification est refusée) ; `CreditSaleCancelled` →
  Annulée (depuis En cours, Soldée ou En perte), versements « à rembourser » si demandé ;
  `CreditSaleReturned` → baisse **plafonnée au reste réel** (jamais négatif, l'excédent n'est pas
  un crédit client au Lot 1).
- **Règles tranchées** : statut calculé (Annulée > En perte > Soldée > En cours) ; reste =
  initial - versements valides, aussi après la perte (Q-22 : plafond des récupérations, statut
  reste En perte) ; Q-19 : 30 jours → « moins de 30 » ; « sans versement depuis 30 jours » =
  dernier versement (ou ouverture) avant J-30 ; reçu : total déjà versé = acompte + versements
  jusqu'à celui-ci (SCN-07 : 500 000) ; portée « Siennes » = vendeur responsable (Q-21) ; pièces
  d'identité des garants : propriétaire et vendeur responsable.
- **Dû client** : `ReceivableCustomerDebt` (restes des créances En cours) sert le plafond de crédit.
- **Rappels** (TR-19) : `ReceivablesModule.dispatch_reminders.execute(shop_id, today)` — alerte
  « Rappel créance » au vendeur responsable et aux propriétaires, une fois par date
  (`alerted_for` + `dedup_key`) ; un report réarme l'alerte.
- **Migration** `0009_receivables` (après `0008_sales`, tête parallèle à `0010_sales_returns`).

## Couches

| Package | Peut importer |
| --- | --- |
| `app.domain` | bibliothèque standard uniquement |
| `app.application` | `domain` |
| `app.infrastructure` | `application`, `domain` |
| `app.interface` | `application`, `domain`, `bootstrap.config` |
| `app.bootstrap` | tout (composition root) |
