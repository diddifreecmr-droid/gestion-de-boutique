"""Clés de recherche, de tri et d'unicité des articles (portables, calculées par le domaine).

**Pliage** (`fold`) : décomposition Unicode NFKD, accents retirés, `casefold`, tout caractère
non alphanumérique remplacé par une espace, espaces réduites. « Haojue  HJ125-8 », « haojue
hj125 8 » et « HAOJUE hj125-8 » ont la même clé (recette CAT-02, décision Q-33 retenue :
casse, accents, espaces et ponctuation ignorés).

Pourquoi des colonnes calculées plutôt qu'une recherche « insensible » côté base ? `ILIKE`,
`unaccent` ou les collations ne sont pas portables (specs § 5.1) : la base ne compare ici que
des chaînes déjà pliées, avec un `LIKE '%…%'` ordinaire. Le terme cherché est plié de la même
façon ; il ne contient donc jamais `%` ni `_` (aucun échappement nécessaire).
"""

import unicodedata
from collections.abc import Iterable

KEY_MAX_LENGTH = 250


def fold(text: str) -> str:
    """Forme pliée d'un texte : sans accent, sans casse, sans ponctuation."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    spaced = "".join(char if char.isalnum() else " " for char in plain.casefold())
    return " ".join(spaced.split())


def search_key(parts: Iterable[str | None]) -> str:
    """Clé de recherche : parties pliées, dans l'ordre, séparées par une espace."""
    folded = (fold(part) for part in parts if part)
    return " ".join(part for part in folded if part)[:KEY_MAX_LENGTH]


def sort_key(display_name: str) -> str:
    """Clé de tri alphabétique : nom plié **sans espace**.

    Sans espace ni ponctuation, l'ordre ne dépend pas de la collation de la base (un
    PostgreSQL en `fr_FR.UTF-8` ignore les espaces au premier niveau, Python non) : la
    pagination par curseur donne le même ordre sur chaque adaptateur.
    """
    return fold(display_name).replace(" ", "")[:KEY_MAX_LENGTH]


def identity_key(*parts: str) -> str:
    """Clé d'unicité (marque + modèle, référence) : parties pliées jointes par `|`."""
    return "|".join(fold(part) for part in parts)[:KEY_MAX_LENGTH]
