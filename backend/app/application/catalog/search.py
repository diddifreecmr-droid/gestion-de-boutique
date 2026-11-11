"""Recherche d'articles : filtre, ordre alphabétique et pagination par curseur (TR-20, § 6.1).

- Texte : recherché **dès la première lettre**, en sous-chaîne, dans la clé pliée du nom, de la
  marque, du modèle et de la référence (`domain/catalog/keys.py`) : insensible à la casse, aux
  accents et à la ponctuation, sur toute base (aucun `ILIKE`/`unaccent`).
- Statut : `ACTIVE` par défaut (listes de vente et d'achat, UC-STK-04) ; `None` = tous.
- Ordre : nom plié croissant puis identifiant ; le curseur est la position `(clé, id)` du
  dernier article servi, opaque pour le client (base64 URL). Curseur illisible → 400.
"""

import base64
import binascii
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.application.ports.pagination import DEFAULT_LIMIT, MAX_LIMIT
from app.domain.catalog.article import Article
from app.domain.catalog.details import ArticleStatus
from app.domain.catalog.keys import fold
from app.domain.shared.errors import ValidationFailed

TEXT_MAX_LENGTH = 100
_SEPARATOR = "|"


@dataclass(frozen=True, slots=True)
class ArticleQuery:
    text: str | None = None
    status: ArticleStatus | None = ArticleStatus.ACTIVE

    def __post_init__(self) -> None:
        if self.text is not None and len(self.text) > TEXT_MAX_LENGTH:
            msg = f"Recherche de {TEXT_MAX_LENGTH} caractères au plus"
            raise ValidationFailed(msg, details={"field": "q"})

    @property
    def folded_text(self) -> str | None:
        """Terme plié ; `None` si vide (aucun filtre de texte)."""
        folded = "" if self.text is None else fold(self.text)
        return folded or None

    def matches(self, article: Article) -> bool:
        """Sémantique de référence (adaptateur mémoire, tests)."""
        text = self.folded_text
        return (self.status is None or article.status is self.status) and (
            text is None or text in article.details.search_key
        )


@dataclass(frozen=True, slots=True, order=True)
class ArticleCursor:
    sort_key: str
    id: UUID

    def encode(self) -> str:
        raw = f"{self.sort_key}{_SEPARATOR}{self.id}".encode()
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @classmethod
    def decode(cls, text: str) -> "ArticleCursor":
        try:
            padded = text + "=" * (-len(text) % 4)
            raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
            key, separator, ident = raw.rpartition(_SEPARATOR)
            if not separator:
                raise ValueError(raw)  # noqa: TRY301 — même traduction que les autres échecs
            return cls(key, UUID(ident))
        except (ValueError, UnicodeError, binascii.Error) as exc:
            msg = "Curseur de pagination illisible"
            raise ValidationFailed(msg, details={"field": "cursor"}) from exc

    @classmethod
    def of(cls, article: Article) -> "ArticleCursor":
        return cls(article.details.sort_key, article.id.value)


@dataclass(frozen=True, slots=True)
class ArticlePageRequest:
    limit: int = DEFAULT_LIMIT
    after: ArticleCursor | None = None

    def __post_init__(self) -> None:
        if isinstance(self.limit, bool) or not isinstance(self.limit, int):
            msg = "ArticlePageRequest.limit doit être un int"
            raise TypeError(msg)
        if not 1 <= self.limit <= MAX_LIMIT:
            msg = f"limit doit être entre 1 et {MAX_LIMIT}"
            raise ValidationFailed(msg, details={"field": "limit", "max": MAX_LIMIT})

    @classmethod
    def parse(cls, cursor: str | None, limit: int | None) -> "ArticlePageRequest":
        after = None if cursor is None else ArticleCursor.decode(cursor)
        return cls(DEFAULT_LIMIT if limit is None else limit, after)


@dataclass(frozen=True, slots=True)
class ArticlePage:
    items: Sequence[Article]
    next_cursor: ArticleCursor | None


def page_of(fetched: Sequence[Article], request: ArticlePageRequest) -> ArticlePage:
    """Page à partir de `limit + 1` articles lus dans l'ordre : le surplus signale la suite."""
    items = list(fetched[: request.limit])
    has_more = len(fetched) > request.limit
    return ArticlePage(items, ArticleCursor.of(items[-1]) if has_more and items else None)


def paginate(articles: Sequence[Article], request: ArticlePageRequest) -> ArticlePage:
    """Trie, saute jusqu'au curseur et découpe (adaptateur mémoire)."""
    ordered = sorted(articles, key=ArticleCursor.of)
    after = request.after
    remaining = [a for a in ordered if after is None or ArticleCursor.of(a) > after]
    return page_of(remaining[: request.limit + 1], request)
