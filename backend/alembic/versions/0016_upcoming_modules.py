"""Modules à venir : `transfers`, `transport`, `import` retirés des boutiques (specs § 15.1).

Révision : 0016_upcoming_modules
Précédente : 0015_mandatory_modules
Créée le : 2026-11-13

Décision client du 2026-11-13 : on ne montre jamais ce qui n'existe pas. Ces trois modules
n'ont encore aucun écran (Lot 2/3) ; une boutique ouverte avant la décision les avait actifs
(profil Motos : tous les modules). Sans ce retrait, l'agrégat `Shop` refuserait de se charger
(invariant, fail-fast). Aucun schéma ne change. Le retour arrière ne remet rien : un module à
venir ne s'active pas.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_upcoming_modules"
down_revision: str | None = "0015_mandatory_modules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPCOMING = ("import", "transfers", "transport")

_shop = sa.table("shop", sa.column("id", sa.Uuid), sa.column("enabled_modules", sa.JSON))


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.select(_shop.c.id, _shop.c.enabled_modules)).all()
    for shop_id, stored in rows:
        modules = json.loads(stored) if isinstance(stored, str) else stored
        if not isinstance(modules, list):
            msg = f"enabled_modules illisible pour la boutique {shop_id} : {stored!r}"
            raise TypeError(msg)
        if set(modules) & set(UPCOMING):
            kept = sorted(set(modules) - set(UPCOMING))
            connection.execute(
                _shop.update().where(_shop.c.id == shop_id).values(enabled_modules=kept)
            )


def downgrade() -> None:
    """Rien à remettre : un module à venir ne s'active pas (voir l'en-tête)."""
