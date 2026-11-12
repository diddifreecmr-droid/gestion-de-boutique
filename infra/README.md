# Infrastructure de développement locale

PostgreSQL et un stockage objet compatible S3 pour développer et tester le backend
(tâche T06, `docs/plan-lot1.md`). Production : voir `specs.md` § 4.7 (hors de ce dossier pour l'instant).

| Service | Image | Rôle | Ports (127.0.0.1 seulement) |
| --- | --- | --- | --- |
| `postgres` | `postgres:18.6-alpine` | bases `boutique` (dev) et `boutique_test` (tests) | 5432 |
| `minio` | `pgsty/silo:RELEASE.2026-11-09T00-00-00Z` | stockage S3 (fork de MinIO) | 9000 (API S3), 9001 (console) |
| `minio-init` | `pgsty/mc:RELEASE.2026-11-09T00-00-00Z` | one-shot : crée le bucket privé `attachments` | — |

> **Pourquoi Silo et pas `minio/minio` ?** Le projet MinIO ne publie plus d'image
> (`minio/minio` et `minio/mc` n'existent plus sur Docker Hub ; quay.io refuse les pulls anonymes).
> Silo est le fork communautaire maintenu par PGSTY : même binaire d'origine, même API S3,
> mêmes variables `MINIO_*`, client `mc`/`mcli`. Le backend ne voit qu'un endpoint S3 (port `FileStorage`, D16).

## Prérequis

- Docker Desktop **démarré** (Docker Engine + Compose v2).
- Un fichier `infra/.env` (jamais commité, ignoré par `.gitignore`) :

```bash
cp infra/.env.example infra/.env   # identifiants factices de dev
```

Toute variable manquante fait échouer la commande avec un message explicite
(`required variable POSTGRES_PASSWORD is missing a value: …`). Aucun secret n'a de valeur par défaut.

## Commandes (depuis la racine du dépôt)

```bash
# Démarrer (attend les healthchecks ; minio-init crée le bucket puis s'arrête)
docker compose -f infra/docker-compose.dev.yml up -d --wait postgres minio
docker compose -f infra/docker-compose.dev.yml up minio-init

# État / journaux
docker compose -f infra/docker-compose.dev.yml ps
docker compose -f infra/docker-compose.dev.yml logs -f postgres

# Console psql
docker compose -f infra/docker-compose.dev.yml exec postgres psql -U boutique -d boutique -c '\l'

# Arrêter (les données sont conservées dans les volumes)
docker compose -f infra/docker-compose.dev.yml down

# Réinitialiser : supprime les volumes pg_data et minio_data (TOUTES les données locales)
docker compose -f infra/docker-compose.dev.yml down -v
```

`.env` est lu dans `infra/` (répertoire du fichier compose), même lancé depuis la racine.
Le script `postgres/init/01-create-test-db.sh` ne s'exécute qu'à la **création** du volume :
après avoir changé `POSTGRES_TEST_DB`, faire `down -v`.

## Configuration attendue par le backend

Valeurs correspondant à `.env.example` (à reporter dans la configuration du backend, `backend/.env`) :

```dotenv
# SQLAlchemy 2 + psycopg 3
DATABASE_URL=postgresql+psycopg://boutique:boutique-dev-password@127.0.0.1:5432/boutique
TEST_DATABASE_URL=postgresql+psycopg://boutique:boutique-dev-password@127.0.0.1:5432/boutique_test

# Stockage objet (API S3)
S3_ENDPOINT=http://127.0.0.1:9000
S3_ACCESS_KEY=boutique-dev
S3_SECRET_KEY=boutique-dev-secret
S3_BUCKET=attachments
S3_REGION=us-east-1
# Adressage par chemin obligatoire (http://hôte/bucket/clé), pas de sous-domaine
S3_ADDRESSING_STYLE=path
```

- Utiliser `127.0.0.1` plutôt que `localhost` (évite une résolution IPv6 `::1` non publiée).
- Le bucket est **privé** (`mc anonymous set none`) : les fichiers ne sont servis que par URL signée courte
  après contrôle des droits (TR-17, § 8.4).
- Console web : http://127.0.0.1:9001 (identifiants `MINIO_ROOT_*`).

## Production

`docker-compose.prod.yml` (une seule stack : caddy, api, postgres, silo, silo-init, backup),
`Caddyfile`, `backup/` (sauvegarde et restauration), `.env.prod.example` (variables, valeurs
factices). Procédure : [`docs/deploiement.md`](../docs/deploiement.md). Vérification locale :

```bash
docker compose --env-file infra/.env.prod.example -f infra/docker-compose.prod.yml config -q
```

## Hors périmètre (à venir)

- Rôle de base de données applicatif sans `UPDATE`/`DELETE` sur `audit_entry` (§ 8.4) : créé par les migrations Alembic.
- Conteneur `worker` (planificateur) et copie hors site des sauvegardes (§ 9.2, étape 2).
