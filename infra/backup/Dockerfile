# syntax=docker/dockerfile:1
# Image « backup » (T25, specs § 9.2 étape 1) : mêmes outils pg_dump / pg_restore que le
# serveur (même version majeure 18). Contexte de build : infra/backup/.
FROM postgres:18.6-alpine

COPY backup.sh restore.sh /usr/local/bin/
# /backups appartient à `postgres` (uid 70) : le volume nommé hérite de ces droits à sa création.
RUN chmod 0755 /usr/local/bin/backup.sh /usr/local/bin/restore.sh \
    && mkdir -p /backups \
    && chown postgres:postgres /backups \
    && chmod 0700 /backups

ENV BACKUP_DIR=/backups \
    TZ=UTC
USER postgres
WORKDIR /backups

# Sain si la dernière sauvegarde réussie date de moins de 26 h (une sauvegarde est faite dès le
# démarrage, puis chaque nuit).
HEALTHCHECK --interval=5m --timeout=10s --start-period=10m --retries=1 \
    CMD test -n "$(find /backups/.last-success -mmin -1560 2>/dev/null)"

ENTRYPOINT ["/usr/local/bin/backup.sh"]
CMD ["loop"]
