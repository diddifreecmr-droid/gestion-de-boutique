#!/bin/sh
# Sauvegarde de nuit de la base (specs § 9.2, étape 1 : copie locale au VPS, volume dédié).
#
# - pg_dump au format « custom » (-Fc, compressé -Z 9), écrit dans un fichier temporaire puis
#   renommé : un fichier boutique-*.dump présent est toujours complet ;
# - contrôle de lecture (pg_restore --list) avant de garder le fichier ;
# - rotation : seules les BACKUP_KEEP copies les plus récentes sont gardées ;
# - .last-success daté à chaque réussite : lu par le healthcheck du conteneur.
#
# Fail-fast : toute erreur (variable absente, base injoignable, dump illisible) arrête le
# script avec un code non nul ; en mode « boucle », le conteneur s'arrête et Docker le
# redémarre (restart: unless-stopped), visible dans Portainer (compteur de redémarrages).
#
# Usage : backup.sh loop   (défaut : une sauvegarde au démarrage, puis chaque nuit)
#         backup.sh once   (une sauvegarde immédiate, ex. avant une mise à jour)
set -eu

: "${PGHOST:?PGHOST manquant}"
: "${PGUSER:?PGUSER manquant}"
: "${PGPASSWORD:?PGPASSWORD manquant}"
: "${PGDATABASE:?PGDATABASE manquant}"
: "${BACKUP_DIR:?BACKUP_DIR manquant}"
: "${BACKUP_KEEP:?BACKUP_KEEP manquant}"
: "${BACKUP_TIME_UTC:?BACKUP_TIME_UTC manquant (HH:MM, heure UTC)}"

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) backup: $*"; }
fail() { log "ÉCHEC : $*" >&2; exit 1; }

case "$BACKUP_KEEP" in
  '' | *[!0-9]*) fail "BACKUP_KEEP doit être un entier ≥ 1 (reçu « $BACKUP_KEEP »)" ;;
esac
[ "$BACKUP_KEEP" -ge 1 ] || fail "BACKUP_KEEP doit être ≥ 1"
case "$BACKUP_TIME_UTC" in
  [0-1][0-9]:[0-5][0-9] | 2[0-3]:[0-5][0-9]) ;;
  *) fail "BACKUP_TIME_UTC doit être au format HH:MM (reçu « $BACKUP_TIME_UTC »)" ;;
esac
[ -d "$BACKUP_DIR" ] && [ -w "$BACKUP_DIR" ] || fail "dossier $BACKUP_DIR absent ou non inscriptible"

backup_once() {
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  final="$BACKUP_DIR/${PGDATABASE}-${stamp}.dump"
  partial="$final.partial"
  log "début de la sauvegarde de « $PGDATABASE » sur $PGHOST"
  pg_dump --format=custom --compress=9 --no-owner --file="$partial" \
    || { rm -f "$partial"; fail "pg_dump a échoué"; }
  pg_restore --list "$partial" > /dev/null \
    || { rm -f "$partial"; fail "dump illisible par pg_restore"; }
  mv "$partial" "$final"
  touch "$BACKUP_DIR/.last-success"
  log "sauvegarde écrite : $final ($(du -h "$final" | cut -f1))"
  rotate
}

rotate() {
  # Noms horodatés (UTC, ordre lexicographique = ordre chronologique) : les plus anciens d'abord.
  count=$(find "$BACKUP_DIR" -maxdepth 1 -name "${PGDATABASE}-*.dump" | wc -l)
  excess=$((count - BACKUP_KEEP))
  [ "$excess" -gt 0 ] || return 0
  find "$BACKUP_DIR" -maxdepth 1 -name "${PGDATABASE}-*.dump" | sort | head -n "$excess" \
    | while read -r old; do
        rm -f "$old"
        log "rotation : $old supprimé (au-delà de $BACKUP_KEEP copies)"
      done
}

seconds_until_next_run() {
  hours=${BACKUP_TIME_UTC%%:*}
  minutes=${BACKUP_TIME_UTC##*:}
  now=$(date -u +%s)
  # ${x#0} : « 08 » → « 8 » (un zéro initial serait lu en octal par l'arithmétique du shell).
  target=$((now - now % 86400 + ${hours#0} * 3600 + ${minutes#0} * 60))
  [ "$target" -gt "$now" ] || target=$((target + 86400))
  echo $((target - now))
}

case "${1:-loop}" in
  once) backup_once ;;
  loop)
    backup_once
    while true; do
      wait_for=$(seconds_until_next_run)
      log "prochaine sauvegarde dans ${wait_for} s (chaque jour à $BACKUP_TIME_UTC UTC)"
      sleep "$wait_for"
      backup_once
    done
    ;;
  *) fail "argument inconnu « $1 » (attendu : loop ou once)" ;;
esac
