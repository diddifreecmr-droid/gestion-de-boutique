"""Table de la synchronisation hors connexion (T23, migration `0013_sync`) — specs § 6.5.

`sync_operation` : une ligne par `op_id` reçu (clé primaire = identifiant client UUIDv7, clé
d'idempotence de `POST /sync`, TR-11). Garde le type, l'origine (auteur, appareil, heure de
saisie et de réception, H12), le numéro provisoire (RG-T06) et le résultat : document créé +
numéro définitif (`accepted`) ou code et motif du refus (`rejected`). Index `(shop_id,
provisional_number)` : retrouver un numéro provisoire (dépenses comprises). Aucune clé
étrangère, comme pour le reste du schéma.
"""

import sqlalchemy as sa

from app.infrastructure.persistence.sqlalchemy.schema import metadata

_TS = sa.DateTime(timezone=True)

sync_operation = sa.Table(
    "sync_operation",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("shop_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("op_type", sa.String(32), nullable=False),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("provisional_number", sa.String(32), nullable=True),
    sa.Column("created_by", sa.Uuid, nullable=False),
    sa.Column("device_id", sa.Uuid, nullable=False),
    sa.Column("captured_at", _TS, nullable=False),
    sa.Column("received_at", _TS, nullable=False),
    sa.Column("entity_id", sa.Uuid, nullable=True),
    sa.Column("number", sa.String(16), nullable=True),
    sa.Column("error_code", sa.String(64), nullable=True),
    sa.Column("error_message", sa.String(500), nullable=True),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.Index("sync_operation_shop_provisional_idx", "shop_id", "provisional_number"),
)
