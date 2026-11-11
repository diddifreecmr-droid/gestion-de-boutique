"""Décisions client (specs § 15.1) : accord sous le prix minimum en réglage, nom d'article unique.

Révision : 0012_min_price_rules
Précédente : 0011_reporting_indexes
Créée le : 2026-11-11

- `shop_settings.min_price_requires_approval` (booléen, **faux** pour toutes les boutiques,
  existantes comprises) : sous le minimum, avertissement et vente acceptée ; vrai = accord du
  propriétaire (T16b).
- `article.name_key` : nom affiché plié (casse, accents, espaces, ponctuation ignorés) des
  articles **sans modèle** (prêt-à-porter, textile), contrainte `article_name`
  `UNIQUE (shop_id, name_key)` (= `UniqueKey` du port du catalogue).

Articles déjà en doublon de nom dans une base existante : la migration **échoue** en les
listant (aucune donnée n'est modifiée) ; le propriétaire renomme puis relance. Le pliage est
recopié ici (et non importé de `app.domain`) : une migration ne doit pas changer après coup.
"""

import unicodedata
from collections import defaultdict
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_min_price_rules"
down_revision: str | None = "0011_reporting_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_KEY_MAX_LENGTH = 250


def _name_key(display_name: str) -> str:
    """Copie figée de `identity_key(display_name)` (`app/domain/catalog/keys.py`)."""
    decomposed = unicodedata.normalize("NFKD", display_name)
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    spaced = "".join(char if char.isalnum() else " " for char in plain.casefold())
    return " ".join(spaced.split())[:_KEY_MAX_LENGTH]


def _fill_name_keys() -> None:
    article = sa.table(
        "article",
        sa.column("id", sa.Uuid),
        sa.column("shop_id", sa.Uuid),
        sa.column("display_name", sa.String),
        sa.column("model", sa.String),
        sa.column("name_key", sa.String),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(article.c.id, article.c.shop_id, article.c.display_name).where(
            article.c.model.is_(None)
        )
    ).all()
    groups: dict[tuple[object, str], list[str]] = defaultdict(list)
    for row in rows:
        groups[(row.shop_id, _name_key(row.display_name))].append(f"{row.display_name} ({row.id})")
    duplicates = [
        f"boutique {shop_id} : {' / '.join(sorted(names))}"
        for (shop_id, _key), names in sorted(groups.items(), key=lambda item: str(item[0]))
        if len(names) > 1
    ]
    if duplicates:
        msg = (
            "Articles de même nom dans une boutique : renommez-les avant de migrer — "
            + " ; ".join(duplicates)
        )
        raise RuntimeError(msg)
    for row in rows:
        bind.execute(
            article.update()
            .where(article.c.id == row.id)
            .values(name_key=_name_key(row.display_name))
        )


def upgrade() -> None:
    op.add_column(
        "shop_settings",
        sa.Column(
            "min_price_requires_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("article", sa.Column("name_key", sa.String(250), nullable=True))
    _fill_name_keys()
    with op.batch_alter_table("article") as batch:  # SQLite : copie de table (tests)
        batch.create_unique_constraint("article_name", ["shop_id", "name_key"])


def downgrade() -> None:
    with op.batch_alter_table("article") as batch:
        batch.drop_constraint("article_name", type_="unique")
        batch.drop_column("name_key")
    op.drop_column("shop_settings", "min_price_requires_approval")
