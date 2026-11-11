#!/bin/sh
# Exécuté une seule fois, à la création du volume pg_data.
# Crée la base de test séparée (tests de contrat --backend=postgres).
set -eu

: "${POSTGRES_TEST_DB:?POSTGRES_TEST_DB manquant}"
: "${POSTGRES_USER:?POSTGRES_USER manquant}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v test_db="$POSTGRES_TEST_DB" -v owner="$POSTGRES_USER" <<'SQL'
CREATE DATABASE :"test_db" OWNER :"owner" ENCODING 'UTF8' TEMPLATE template0;
SQL

echo "Base de test \"$POSTGRES_TEST_DB\" créée."
