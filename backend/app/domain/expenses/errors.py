"""Erreurs métier du module Dépenses (codes **ajoutés** par T18, recette Q-31).

| Erreur | Code | HTTP | Cas |
| --- | --- | --- | --- |
| `DescriptionRequired` | `DESCRIPTION_REQUIRED` | 400 | « Autre » sans description (UC-DEP-01) |
| `ReasonRequired` | `REASON_REQUIRED` | 400 | annulation sans motif (UC-DEP-04) |
| `CorrectionWindowClosed` | `CORRECTION_WINDOW_CLOSED` | 422 | auteur après minuit (Douala) |
| `BaseCategoryLocked` | `BASE_CATEGORY_LOCKED` | 422 | désactiver une catégorie de base |
| `InactiveReference` | `INACTIVE_REFERENCE` | 422 | catégorie, mode ou lieu désactivé |
| `InvalidTagMerge` | `INVALID_TAG_MERGE` | 422 | fusion dans lui-même ou dans un tag fusionné |
"""

from datetime import datetime

from app.domain.shared.errors import DomainError, ValidationFailed


class DescriptionRequired(ValidationFailed):
    code = "DESCRIPTION_REQUIRED"

    def __init__(self) -> None:
        super().__init__("Cette catégorie exige une description", details={"field": "description"})


class ReasonRequired(ValidationFailed):
    code = "REASON_REQUIRED"

    def __init__(self) -> None:
        super().__init__("Le motif est obligatoire", details={"field": "reason"})


class CorrectionWindowClosed(DomainError):
    code = "CORRECTION_WINDOW_CLOSED"

    def __init__(self, deadline: datetime) -> None:
        super().__init__(
            "Délai dépassé : seul le propriétaire peut encore modifier cette dépense",
            details={"deadline": deadline.isoformat()},
        )


class BaseCategoryLocked(DomainError):
    code = "BASE_CATEGORY_LOCKED"

    def __init__(self, category: str) -> None:
        super().__init__(
            "Une catégorie de base se renomme mais ne se désactive pas",
            details={"category_id": category},
        )


class InactiveReference(DomainError):
    code = "INACTIVE_REFERENCE"

    def __init__(self, field: str, value: str) -> None:
        super().__init__(
            "Élément désactivé : choisissez-en un autre", details={"field": field, "id": value}
        )


class InvalidTagMerge(DomainError):
    code = "INVALID_TAG_MERGE"

    def __init__(self, reason: str) -> None:
        super().__init__("Fusion de tags impossible", details={"reason": reason})
