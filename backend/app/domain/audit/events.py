"""Contrat « événement journalisable » : la traduction événement → journal (TR-09, RG-T01).

**Choix : l'événement se décrit lui-même.** Un événement de domaine qui doit laisser une trace
hérite d'`AuditableEvent` et implémente `audit_record()` ; celui qui, délibérément, n'en laisse
pas hérite de `NotAudited`. Le handler `AuditRecorder` refuse tout autre événement
(`UnauditedEvent`, transaction annulée) : oublier de décider est une erreur qui échoue vite,
jamais un trou silencieux dans le journal.

Pourquoi pas un registre de traducteurs par type ? La phrase du journal (élément, numéro,
avant/après, motif) dépend de l'état que seul l'agrégat connaît au moment de l'événement ; le
placer à côté de l'événement garde la règle et sa trace dans le même module, et un module ne
peut pas être livré sans avoir tranché (le test d'un événement suffit à le prouver).

    @dataclass(frozen=True, kw_only=True)
    class SaleRecorded(DomainEvent, AuditableEvent):
        performer: Performer
        number: DocNumber
        ...
        def audit_record(self) -> AuditRecord:
            return AuditRecord(performer=self.performer, action=AuditAction.CREATE, ...)
"""

from abc import ABC, abstractmethod

from app.domain.audit.entry import AuditRecord


class AuditableEvent(ABC):
    """Mixin d'un `DomainEvent` qui crée une entrée de journal."""

    __slots__ = ()

    @abstractmethod
    def audit_record(self) -> AuditRecord:
        """Ce que le journal doit retenir de cet événement (une entrée)."""


class NotAudited:
    """Mixin d'un `DomainEvent` qui, par décision explicite, ne crée aucune entrée."""

    __slots__ = ()


class UnauditedEvent(RuntimeError):
    """Événement ni `AuditableEvent` ni `NotAudited` : décision de journalisation manquante."""
