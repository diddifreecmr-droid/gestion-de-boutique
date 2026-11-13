"""Modules toujours actifs : `catalog` et `sales` rejoignent `core` et `audit` (specs § 15.1).

Révision : 0015_mandatory_modules
Précédente : 0014_attachments
Créée le : 2026-11-12

Décision client du 2026-11-12 : socle, journal, catalogue et ventes ne se désactivent jamais.
Une boutique réglée avant cette décision sans `catalog` ou `sales` les retrouve ; sans cela
l'agrégat `Shop` refuserait de se charger (invariant, fail-fast). Aucun schéma ne change.
Le retour arrière ne retire rien : on ne sait plus quels modules avaient été désactivés.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015_mandatory_modules"
down_revision: str | None = "0014_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MANDATORY = ("audit", "catalog", "core", "sales")

_shop = sa.table("shop", sa.column("id", sa.Uuid), sa.column("enabled_modules", sa.JSON))


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.select(_shop.c.id, _shop.c.enabled_modules)).all()
    for shop_id, stored in rows:
        modules = json.loads(stored) if isinstance(stored, str) else stored
        if not isinstance(modules, list):
            msg = f"enabled_modules illisible pour la boutique {shop_id} : {stored!r}"
            raise TypeError(msg)
        completed = sorted(set(modules) | set(MANDATORY))
        if completed != sorted(modules):
            connection.execute(
                _shop.update().where(_shop.c.id == shop_id).values(enabled_modules=completed)
            )


def downgrade() -> None:
    """Rien à défaire : les modules ajoutés restent actifs (voir l'en-tête)."""
