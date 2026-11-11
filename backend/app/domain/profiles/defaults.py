"""Listes de départ communes à tous les profils (RG-T19, CDC § 20.1 et § 20.6), libellés."""

from app.domain.profiles.fields import FieldKind, FieldSpec
from app.domain.profiles.profile import PaymentModeTemplate
from app.domain.shared.roles import Role

PAYMENT_MODES = (
    PaymentModeTemplate("Espèces", reference_required=False),
    PaymentModeTemplate("Orange Money", reference_required=True),
    PaymentModeTemplate("MTN Mobile Money", reference_required=True),
    PaymentModeTemplate("Virement", reference_required=True),
    PaymentModeTemplate("Chèque", reference_required=True),
    PaymentModeTemplate("Autre", reference_required=False),
)
"""RG-T19 : la référence est **proposée** (jamais obligatoire) quand `reference_required`."""

EXPENSE_CATEGORIES = ("Carburant", "Repas", "Salaire", "Loyer", "Autre")
"""Catégories de base (UC-DEP-02) : renommables, jamais désactivables."""

SELLER_LABELS = {
    Role.OWNER: "Propriétaire",
    Role.SELLER: "Vendeur",
    Role.ACCOUNTANT: "Comptable",
    Role.DRIVER: "Chauffeur",
}
EMPLOYEE_LABELS = {
    Role.OWNER: "Propriétaire",
    Role.SELLER: "Employé",
    Role.ACCOUNTANT: "Comptable",
}

COLOR = FieldSpec("color", "Couleur", FieldKind.TEXT)
CATEGORY = FieldSpec("category", "Catégorie", FieldKind.TEXT)
REFERENCE = FieldSpec("reference", "Référence", FieldKind.TEXT, unique=True)
