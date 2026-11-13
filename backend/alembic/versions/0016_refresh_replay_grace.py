"""Rejeu toléré du jeton de rafraîchissement : jeton remplacé et instant de rotation (§ 8.1).

Révision : 0016_refresh_replay_grace
Précédente : 0015_mandatory_modules
Créée le : 2026-11-13

Audit du 2026-11-13 : une réponse de `/auth/refresh` perdue laissait l'ancien cookie au
navigateur, et le rafraîchissement suivant révoquait la session. `device_session` garde
l'empreinte du jeton que la dernière rotation a remplacé (`previous_refresh_hash`) et
l'instant de cette rotation (`rotated_at`) ; vides pour les sessions existantes (aucun rejeu
toléré avant leur prochaine rotation).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_refresh_replay_grace"
down_revision: str | None = "0015_mandatory_modules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "device_session", sa.Column("previous_refresh_hash", sa.String(128), nullable=True)
    )
    op.add_column(
        "device_session", sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("device_session", "rotated_at")
    op.drop_column("device_session", "previous_refresh_hash")
