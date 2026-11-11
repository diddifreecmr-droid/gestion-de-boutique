"""Pagination par curseur (specs § 6.1 : `?cursor=&limit=` → `{items, next_cursor}`).

Listes triées du plus récent au plus ancien sur `(instant, id)` ; le curseur est la position
du dernier élément servi. Sa forme texte est **opaque** pour le client (base64 URL de
`<instant ISO>|<uuid>`) ; un curseur illisible lève `ValidationFailed` (400), jamais un repli
silencieux sur la première page.
"""

import base64
import binascii
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.shared.business_day import require_aware
from app.domain.shared.errors import ValidationFailed

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
_SEPARATOR = "|"


@dataclass(frozen=True, slots=True, order=True)
class Cursor:
    """Position `(at, id)` du dernier élément servi ; la page suivante est strictement après."""

    at: datetime
    id: UUID

    def __post_init__(self) -> None:
        object.__setattr__(self, "at", require_aware(self.at))
        if not isinstance(self.id, UUID):
            msg = "Cursor.id doit être un UUID"
            raise TypeError(msg)

    def encode(self) -> str:
        raw = f"{self.at.isoformat()}{_SEPARATOR}{self.id}".encode()
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @classmethod
    def decode(cls, text: str) -> "Cursor":
        try:
            padded = text + "=" * (-len(text) % 4)
            raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
            at, separator, ident = raw.partition(_SEPARATOR)
            if not separator:
                raise ValueError(raw)  # noqa: TRY301 — même traduction que les autres échecs
            return cls(datetime.fromisoformat(at), UUID(ident))
        except (ValueError, UnicodeError, binascii.Error) as exc:
            msg = "Curseur de pagination illisible"
            raise ValidationFailed(msg, details={"field": "cursor"}) from exc


type PositionOf[T] = Callable[[T], Cursor]


@dataclass(frozen=True, slots=True)
class PageRequest:
    limit: int = DEFAULT_LIMIT
    after: Cursor | None = None

    def __post_init__(self) -> None:
        if isinstance(self.limit, bool) or not isinstance(self.limit, int):
            msg = "PageRequest.limit doit être un int"
            raise TypeError(msg)
        if not 1 <= self.limit <= MAX_LIMIT:
            msg = f"limit doit être entre 1 et {MAX_LIMIT}"
            raise ValidationFailed(msg, details={"field": "limit", "max": MAX_LIMIT})

    @classmethod
    def parse(cls, cursor: str | None, limit: int | None) -> "PageRequest":
        after = None if cursor is None else Cursor.decode(cursor)
        return cls(DEFAULT_LIMIT if limit is None else limit, after)


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: Sequence[T]
    next_cursor: Cursor | None


def paginate[T](ordered: Sequence[T], request: PageRequest, position: PositionOf[T]) -> Page[T]:
    """Découpe une liste **déjà triée du plus récent au plus ancien** (adaptateurs mémoire)."""
    remaining = [
        item for item in ordered if request.after is None or position(item) < request.after
    ]
    return page_of(remaining[: request.limit + 1], request, position)


def page_of[T](fetched: Sequence[T], request: PageRequest, position: PositionOf[T]) -> Page[T]:
    """Page à partir de `limit + 1` éléments lus : le surplus signale une page suivante."""
    items = list(fetched[: request.limit])
    has_more = len(fetched) > request.limit
    return Page(items, position(items[-1]) if has_more and items else None)
