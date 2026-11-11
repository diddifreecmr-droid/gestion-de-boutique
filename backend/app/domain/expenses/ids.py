"""Identifiants typés du module Dépenses (UUIDv7 fournis par le client, specs § 6.1)."""

from app.domain.shared.ids import EntityId


class ExpenseId(EntityId):
    __slots__ = ()


class TagId(EntityId):
    __slots__ = ()


class AttachmentId(EntityId):
    """Pièce jointe (justificatif) ; le module Pièces jointes la stocke (TR-17)."""

    __slots__ = ()
