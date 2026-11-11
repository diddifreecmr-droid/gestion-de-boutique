"""Erreurs techniques des ports : **erreurs de programmation**, jamais des `DomainError`.

Elles signalent un bogue (boutique mélangée, cycle de vie d'unité de travail mal suivi) et
aboutissent à une réponse 500 générique : elles ne doivent jamais être interceptées pour être
traduites en message utilisateur.
"""


class IsolationViolation(RuntimeError):
    """Écriture, lecture ou événement hors de la boutique de l'unité de travail (specs § 8.3)."""


class UnitOfWorkStateError(RuntimeError):
    """Usage incorrect du cycle de vie d'un `UnitOfWork` (commit double, hors `with`…)."""


class UncommittedChanges(UnitOfWorkStateError):
    """Sortie du `with` sans `commit()` ni `rollback()` alors que des écritures attendaient.

    Les écritures sont annulées, puis cette erreur est levée : un oubli de `commit()` ne passe
    jamais inaperçu.
    """


class UnsavedChanges(UnitOfWorkStateError):
    """Agrégat lu, porteur d'événements, jamais repassé à `update` : modification perdue."""
