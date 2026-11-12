#!/bin/sh
# Restauration d'une sauvegarde de backup.sh (specs § 9.2). Procédure : docs/deploiement.md.
#
# Usage (console du conteneur backup, API ARRÊTÉE) :
#   restore.sh                          liste les sauvegardes disponibles
#   restore.sh <fichier.dump> --yes     remplace le contenu de la base par celui du fichier
#
# Fail-fast : sans --yes, sans fichier lisible ou en cas d'erreur de pg_restore, le script
# s'arrête avec un code non nul (--exit-on-error : pas de restauration partielle silencieuse).
set -eu

: "${PGHOST:?PGHOST manquant}"
: "${PGUSER:?PGUSER manquant}"
: "${PGPASSWORD:?PGPASSWORD manquant}"
: "${PGDATABASE:?PGDATABASE manquant}"
: "${BACKUP_DIR:?BACKUP_DIR manquant}"

if [ $# -eq 0 ]; then
  echo "Sauvegardes disponibles dans $BACKUP_DIR (la plus récente en dernier) :"
  find "$BACKUP_DIR" -maxdepth 1 -name "*.dump" | sort
  exit 0
fi

file=$1
case "$file" in
  /*) ;;
  *) file="$BACKUP_DIR/$file" ;;
esac
[ -r "$file" ] || { echo "ÉCHEC : fichier illisible : $file" >&2; exit 1; }
[ "${2:-}" = "--yes" ] || {
  echo "ÉCHEC : la restauration REMPLACE les données de « $PGDATABASE »." >&2
  echo "Arrêtez l'API, puis relancez : restore.sh $1 --yes" >&2
  exit 2
}

pg_restore --list "$file" > /dev/null
echo "Restauration de $file dans « $PGDATABASE » sur $PGHOST…"
pg_restore --clean --if-exists --no-owner --exit-on-error --single-transaction \
  --dbname="$PGDATABASE" "$file"
echo "Restauration terminée. Redémarrez l'API (elle vérifie la base au démarrage)."
