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

## Couches

| Package | Peut importer |
| --- | --- |
| `app.domain` | bibliothèque standard uniquement |
| `app.application` | `domain` |
| `app.infrastructure` | `application`, `domain` |
| `app.interface` | `application`, `domain`, `bootstrap.config` |
| `app.bootstrap` | tout (composition root) |
