"""Identifiants typés du catalogue (UUIDv7, specs D5)."""

from app.domain.shared.ids import EntityId


class ArticleId(EntityId):
    """Article du catalogue (un modèle de moto, un vêtement, un tissu)."""

    __slots__ = ()


class PriceHistoryId(EntityId):
    """Ligne de l'historique des prix d'un article (CDC § 20.2)."""

    __slots__ = ()


class AttachmentId(EntityId):
    """Pièce jointe (photo d'article). Le module Pièces jointes (TR-17) viendra plus tard :
    l'article ne garde que l'identifiant, sans vérifier son existence."""

    __slots__ = ()
