"""Droit d'échange de l'employé (UC-PAP-01, décision client QC-4 du 2026-11-13, T29).

Révision : 0018_exchange_rights
Précédente : 0017_upcoming_modules
Créée le : 2026-11-13

- `shop_settings.employee_exchange_allowed` (booléen, **faux** pour toutes les boutiques,
  existantes comprises) : seul le propriétaire échange ; vrai = le vendeur échange ses propres
  ventes, dans le délai `exchange_days`.

Le délai `exchange_days` existait déjà (colonne inchangée) : il est désormais appliqué par le
cas d'utilisation, sans changement de schéma. Le retour arrière retire la colonne (le réglage
est perdu : l'échange redevient réservé au propriétaire).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018_exchange_rights"
down_revision: str | None = "0017_upcoming_modules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "shop_settings",
        sa.Column(
            "employee_exchange_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("shop_settings", "employee_exchange_allowed")
