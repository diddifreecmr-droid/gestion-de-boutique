"""Tables **plateforme** (sans `shop_id`) : comptes, sessions d'appareil, comptes commerçants.

- `app_user` (`USER` de specs § 5.2 ; `user` est un mot réservé de PostgreSQL) : téléphone
  E.164 unique sur la plateforme (`user_phone`), deux compteurs d'essais **indépendants**
  (connexion ; changement de code, décision du 11/11/2026).
- `device_session` : une session par appareil ; seule l'empreinte du jeton de rafraîchissement,
  et celle du jeton tout juste remplacé avec l'instant de la rotation (rejeu toléré, § 8.1).
- `merchant_account` : offre (`plan`) du compte et noms de ses boutiques (unicité du nom de
  boutique dans le compte, gardée par l'agrégat et son verrou optimiste).
"""

import sqlalchemy as sa

from app.infrastructure.persistence.sqlalchemy.schema import metadata

_TS = sa.DateTime(timezone=True)

app_user = sa.Table(
    "app_user",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("phone", sa.String(16), nullable=False),
    sa.Column("name", sa.String(120), nullable=False),
    sa.Column("secret_hash", sa.String(255), nullable=False),
    sa.Column("is_platform_admin", sa.Boolean, nullable=False),
    sa.Column("must_change_pin", sa.Boolean, nullable=False),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("failed_attempts", sa.Integer, nullable=False),
    sa.Column("locked_until", _TS, nullable=True),
    sa.Column("pin_change_failures", sa.Integer, nullable=False),
    sa.Column("pin_change_locked_until", _TS, nullable=True),
    sa.Column("last_login_at", _TS, nullable=True),
    sa.UniqueConstraint("phone", name="user_phone"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.CheckConstraint(
        "failed_attempts >= 0 AND pin_change_failures >= 0", name="failures_positive"
    ),
)

device_session = sa.Table(
    "device_session",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("user_id", sa.Uuid, nullable=False),
    sa.Column("device_id", sa.Uuid, nullable=False),
    sa.Column("device_label", sa.String(100), nullable=False),
    sa.Column("refresh_hash", sa.String(128), nullable=False),
    sa.Column("created_at", _TS, nullable=False),
    sa.Column("last_seen", _TS, nullable=False),
    sa.Column("expires_at", _TS, nullable=False),
    sa.Column("sliding", sa.Boolean, nullable=False),
    sa.Column("revoked", sa.Boolean, nullable=False),
    sa.Column("revoked_at", _TS, nullable=True),
    sa.Column("previous_refresh_hash", sa.String(128), nullable=True),
    sa.Column("rotated_at", _TS, nullable=True),
    sa.CheckConstraint("version >= 1", name="version_positive"),
    sa.Index("device_session_user_device_idx", "user_id", "device_id"),
)

merchant_account = sa.Table(
    "merchant_account",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("version", sa.BigInteger, nullable=False),
    sa.Column("name", sa.String(120), nullable=False),
    sa.Column("phone", sa.String(16), nullable=False),
    sa.Column("plan", sa.String(16), nullable=False),
    sa.Column("status", sa.String(16), nullable=False),
    sa.Column("shop_names", sa.JSON, nullable=False),
    sa.UniqueConstraint("phone", name="merchant_account_phone"),
    sa.CheckConstraint("version >= 1", name="version_positive"),
)
