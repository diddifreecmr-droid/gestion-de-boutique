"""Matrice CDC § 4.2 cellule par cellule, vérifiée **à travers la `Policy`** (recette SEC-M).

`EXPECTED` est une seconde saisie, indépendante de `role_matrix.py`, du tableau du CDC :
4 lettres dans l'ordre Propriétaire, Vendeur, Comptable, Chauffeur — T = Tout, S = Siens,
L = Lecture, N = « — ». Une divergence entre les deux saisies fait échouer la cellule.
"""

from collections.abc import Mapping

import pytest

from app.application.security.access import Access
from app.application.security.errors import PermissionDenied
from app.application.security.permissions import Mode, Permission
from app.application.security.role_matrix import ROLE_MATRIX, validate_matrix
from app.application.security.roles import Role
from tests.application.security.support import fixed_policy, member

ROLE_ORDER = (Role.OWNER, Role.SELLER, Role.ACCOUNTANT, Role.DRIVER)
LETTERS = {"T": Access.ALL, "S": Access.OWN, "L": Access.READ, "N": Access.NONE}

EXPECTED: Mapping[str, str] = {
    # Gérer les utilisateurs et les réglages de la boutique
    "MEMBER_MANAGE": "TNNN",
    "SETTINGS_MANAGE": "TNNN",
    # Gérer les lieux (boutique, entrepôts) — Q-30
    "LOCATION_READ": "TNLN",
    "LOCATION_MANAGE": "TNNN",
    # Créer et modifier un article ; archivage UC-STK-04
    "ARTICLE_WRITE": "TNTN",
    "ARTICLE_ARCHIVE": "TNNN",
    # Fixer le prix de vente de base et le prix minimum — Q-14
    "PRICE_SET": "TNNN",
    "SELLING_PRICE_READ": "TLNN",
    # Voir le stock disponible (quantités)
    "STOCK_READ": "TLTN",
    # Voir les prix d'achat et la valeur du stock
    "COST_READ": "TNTN",
    "STOCK_VALUE_READ": "TNTN",
    "STOCK_HISTORY_READ": "TNTN",
    # Faire un inventaire, un ajustement de stock
    "INVENTORY_MANAGE": "TNTN",
    "STOCK_ADJUST": "TNTN",
    # Enregistrer un achat, gérer les fournisseurs — Q-13
    "PURCHASE_READ": "TNTN",
    "PURCHASE_WRITE": "TNTN",
    "PURCHASE_CANCEL": "TNNN",
    "SUPPLIER_READ": "TNTN",
    "SUPPLIER_MANAGE": "TNTN",
    # Créer et réceptionner un déplacement de stock (UC-TRF-04 pour l'annulation)
    "TRANSFER_READ": "TNTN",
    "TRANSFER_WRITE": "TNTN",
    "TRANSFER_CANCEL": "TNSN",
    # Enregistrer une vente / Voir les ventes / RG-D03
    "SALE_CREATE": "TSNN",
    "SALE_READ": "TSNN",
    "SALES_DATA_READ": "TSNN",
    # Modifier ou annuler une vente, faire un retour — Q-32
    "SALE_UPDATE": "TNNN",
    "SALE_CANCEL": "TNNN",
    "SALE_RETURN": "TNNN",
    # Échange UC-PAP-01 — QC-4 : vendeur, ses ventes, si réglage (cas d'utilisation)
    "SALE_EXCHANGE": "TSNN",
    "SALE_ERROR_REPORT": "TSNN",
    # Vendre au-dessous du prix minimum (UC-VEN-03)
    "SALE_BELOW_MIN": "TNNN",
    "PRICE_REQUEST_CREATE": "TSNN",
    "PRICE_REQUEST_READ": "TSNN",
    "PRICE_REQUEST_DECIDE": "TNNN",
    # Créer et voir les créances — Q-15, Q-21 ; clients UC-VEN-11
    "RECEIVABLE_READ": "TSNN",
    "RECEIVABLE_CREATE": "TNNN",
    "RECEIVABLE_FOLLOW_UP": "TSNN",
    "CUSTOMER_READ": "TSNN",
    "CUSTOMER_MANAGE": "TSNN",
    # Enregistrer un versement / Annuler un versement, passer une créance en perte
    "INSTALLMENT_CREATE": "TSNN",
    "INSTALLMENT_CANCEL": "TNNN",
    "RECEIVABLE_WRITE_OFF": "TNNN",
    # Enregistrer une dépense journalière — Q-11 ; UC-DEP-02
    "EXPENSE_READ": "TNTN",
    "EXPENSE_CREATE": "TNTN",
    "EXPENSE_CORRECT": "TNSN",
    "EXPENSE_CATEGORY_MANAGE": "TNNN",
    "TAG_READ": "TNTN",
    "TAG_MERGE": "TNNN",
    # Gérer camions et chauffeurs (comptable : liste des noms seulement)
    "FLEET_READ": "TNNN",
    "FLEET_NAMES_READ": "TNLN",
    "FLEET_MANAGE": "TNNN",
    # Créer, suivre et clôturer un voyage / Saisir une étape ou une dépense de voyage
    "TRIP_READ": "TNNS",
    "TRIP_MANAGE": "TNNN",
    "TRIP_STEP_RECORD": "TNNS",
    "TRIP_EXPENSE_RECORD": "TNNS",
    # Valider une dépense de voyage / Primes, avances et paie des chauffeurs
    "TRIP_EXPENSE_VALIDATE": "TNNN",
    "PAYROLL_READ": "TNNN",
    "PAYROLL_MANAGE": "TNNN",
    # RG-D05 : aucun prix pour le chauffeur
    "PRICE_READ": "TLLN",
    # Tableau de bord complet ; accueil et alertes de son rôle
    "DASHBOARD_READ": "TNNN",
    "HOME_READ": "TSSS",
    "ALERT_READ": "TSSS",
    # Importer depuis Excel (comptable : articles, stock, fournisseurs) ; UC-IMP-03
    "IMPORT_ARTICLES": "TNTN",
    "IMPORT_STOCK": "TNTN",
    "IMPORT_SUPPLIERS": "TNTN",
    "IMPORT_CUSTOMERS": "TNNN",
    "IMPORT_RECEIVABLES": "TNNN",
    "IMPORT_FLEET": "TNNN",
    "IMPORT_CANCEL": "TNNN",
    # Journal d'actions
    "AUDIT_READ": "TNNN",
}

CELLS = [
    pytest.param(Permission(name), role, LETTERS[row[index]], id=f"{name}-{role.value}")
    for name, row in EXPECTED.items()
    for index, role in enumerate(ROLE_ORDER)
]


def test_expected_table_covers_every_permission_exactly() -> None:
    assert set(EXPECTED) == {permission.value for permission in Permission}
    assert all(len(row) == len(ROLE_ORDER) for row in EXPECTED.values())
    assert len(CELLS) == len(Permission) * len(Role)


@pytest.mark.parametrize(("permission", "role", "expected"), CELLS)
def test_cell(permission: Permission, role: Role, expected: Access) -> None:
    assert ROLE_MATRIX[permission][role] is expected
    policy, actor = fixed_policy(), member(role)
    if expected is Access.NONE:
        with pytest.raises(PermissionDenied):
            policy.require(actor, permission)
    else:
        assert policy.require(actor, permission) is expected


def test_owner_has_every_permission() -> None:
    assert all(cells[Role.OWNER] is Access.ALL for cells in ROLE_MATRIX.values())


def test_matrix_is_read_only() -> None:
    with pytest.raises(TypeError):
        ROLE_MATRIX[Permission.AUDIT_READ] = {}  # type: ignore[index]  # immuabilité prouvée


def test_validation_rejects_missing_permission() -> None:
    partial: dict[Permission, Mapping[Role, Access]] = dict(ROLE_MATRIX)
    del partial[Permission.AUDIT_READ]
    with pytest.raises(RuntimeError, match="incomplète"):
        validate_matrix(partial)


def test_validation_rejects_missing_role() -> None:
    broken: dict[Permission, Mapping[Role, Access]] = dict(ROLE_MATRIX)
    broken[Permission.AUDIT_READ] = {Role.OWNER: Access.ALL}
    with pytest.raises(RuntimeError, match="chaque rôle"):
        validate_matrix(broken)


def test_validation_rejects_read_on_write_permission() -> None:
    assert Permission.MEMBER_MANAGE.mode is Mode.WRITE
    broken: dict[Permission, Mapping[Role, Access]] = dict(ROLE_MATRIX)
    broken[Permission.MEMBER_MANAGE] = dict.fromkeys(Role, Access.READ)
    with pytest.raises(RuntimeError, match="Lecture"):
        validate_matrix(broken)
