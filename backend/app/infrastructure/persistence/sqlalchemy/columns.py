"""Conversions de colonnes partagées par les adaptateurs SQL.

Instants : l'application n'écrit que de l'UTC aware. PostgreSQL (`timestamptz`) relit un instant
aware ; SQLite (tests sans serveur) n'a pas de type horodaté et relit un `datetime` **naïf** —
c'est l'UTC écrit, on lui rend son fuseau. Toute autre valeur est une erreur d'adaptateur.
"""

from datetime import UTC, datetime

import sqlalchemy as sa

from app.application.ports.pagination import Cursor
from app.domain.shared.business_day import require_aware


def to_db(instant: datetime) -> datetime:
    """Instant à écrire : toujours ramené en UTC (refus d'un instant naïf)."""
    return require_aware(instant)


def from_db(value: object) -> datetime:
    if not isinstance(value, datetime):
        msg = f"Colonne horodatée illisible : {type(value).__name__}"
        raise TypeError(msg)
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def from_db_optional(value: object) -> datetime | None:
    return None if value is None else from_db(value)


def before_cursor(
    at: sa.ColumnElement[datetime], ident: sa.ColumnElement[object], cursor: Cursor
) -> sa.ColumnElement[bool]:
    """Lignes strictement après `cursor` dans l'ordre `(at DESC, id DESC)` (page suivante)."""
    return sa.or_(at < to_db(cursor.at), sa.and_(at == to_db(cursor.at), ident < cursor.id))
