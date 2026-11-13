"""Annulation d'un lot d'import : clés libérées et rapport des lignes refusées (QC-6, T35).

Révision : 0020_import_cancellation
Précédente : 0019_import_batches
Créée le : 2026-11-13

Annuler un lot **archive** ce qu'il a créé (rien n'est effacé) et libère noms, références et
téléphones pour un nouvel import : l'élément retiré n'occupe plus son unicité.

- `article.keys_released` (booléen, faux partout) : article retiré, ses trois clés
  (`brand_model_key`, `name_key`, `reference_key`, déjà nullables) sont écrites `NULL`.
- `customer.phone_key` : copie du téléphone (recopiée pour les clients existants), `NULL` une
  fois le client désactivé ; l'unicité `customer_phone` passe de `phone` à `phone_key`.
- `supplier.name_key` devient nullable : `NULL` une fois le fournisseur retiré.
- `import_problem` : lignes refusées d'un lot (rapport `errors.xlsx`).

Retour arrière : refusé (erreur explicite) si un élément a déjà été retiré — remettre les
anciennes unicités ferait échouer la base sur des doublons légitimes.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020_import_cancellation"
down_revision: str | None = "0019_import_batches"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "article",
        sa.Column("keys_released", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("customer", sa.Column("phone_key", sa.String(length=16), nullable=True))
    op.execute("UPDATE customer SET phone_key = phone")
    with op.batch_alter_table("customer") as batch:
        batch.drop_constraint("customer_phone", type_="unique")
        batch.create_unique_constraint("customer_phone", ["shop_id", "phone_key"])
    with op.batch_alter_table("supplier") as batch:
        batch.alter_column("name_key", existing_type=sa.String(length=120), nullable=True)
    op.create_table(
        "import_problem",
        sa.Column("import_batch_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("line", sa.Integer(), nullable=False),
        sa.Column("column_name", sa.String(length=120), nullable=True),
        sa.Column("message", sa.String(length=300), nullable=False),
        sa.CheckConstraint("line >= 2", name=op.f("import_problem_line_of_data_check")),
        sa.PrimaryKeyConstraint("import_batch_id", "position", name=op.f("import_problem_pkey")),
    )
    op.create_index(
        "import_problem_shop_batch_idx", "import_problem", ["shop_id", "import_batch_id"]
    )


def _require_nothing_released() -> None:
    bind = op.get_bind()
    released = bind.execute(
        sa.text(
            "SELECT (SELECT COUNT(*) FROM article WHERE keys_released)"
            " + (SELECT COUNT(*) FROM customer WHERE phone_key IS NULL)"
            " + (SELECT COUNT(*) FROM supplier WHERE name_key IS NULL)"
        )
    ).scalar_one()
    if released:
        msg = (
            f"Retour arrière de 0020 impossible : {released} élément(s) retiré(s) par"
            " l'annulation d'un import occupent des noms ou téléphones libérés"
        )
        raise RuntimeError(msg)


def downgrade() -> None:
    _require_nothing_released()
    op.drop_index("import_problem_shop_batch_idx", table_name="import_problem")
    op.drop_table("import_problem")
    with op.batch_alter_table("supplier") as batch:
        batch.alter_column("name_key", existing_type=sa.String(length=120), nullable=False)
    with op.batch_alter_table("customer") as batch:
        batch.drop_constraint("customer_phone", type_="unique")
        batch.create_unique_constraint("customer_phone", ["shop_id", "phone"])
        batch.drop_column("phone_key")
    op.drop_column("article", "keys_released")
