"""Permissions vérifiées par la couche application (specs § 8.2, TR-04).

Chaque ligne de la matrice du CDC § 4.2 est découpée en permissions **d'action** assez fines
pour exprimer « Tout / Siens / Lecture / sans le prix de vente » sans valeur d'accès ad hoc :
une ligne « gérer » donne une permission de lecture et une ou plusieurs d'écriture. Les lignes
Lot 2 (transport, déplacements) et Lot 3 (import) sont présentes dès maintenant : aucune route
future ne peut être livrée sans droit déclaré.

Les permissions **de champ** (`COST_READ`, `SALES_DATA_READ`, `PRICE_READ`,
`SELLING_PRICE_READ`, `AUDIT_READ`) servent aux présentateurs (TR-05) via
`Policy.can_read_field`.
"""

from enum import StrEnum, unique


class Mode(StrEnum):
    """Nature de la permission : un accès « Lecture » n'est valide que sur `READ`."""

    READ = "read"
    WRITE = "write"


@unique
class Permission(StrEnum):
    """Code stable d'une permission (journalisé et renvoyé dans `error.details`)."""

    # Boutique : utilisateurs, réglages, lieux
    MEMBER_MANAGE = "MEMBER_MANAGE"
    SETTINGS_MANAGE = "SETTINGS_MANAGE"
    LOCATION_READ = "LOCATION_READ"
    LOCATION_MANAGE = "LOCATION_MANAGE"
    # Catalogue et prix
    ARTICLE_WRITE = "ARTICLE_WRITE"
    ARTICLE_ARCHIVE = "ARTICLE_ARCHIVE"
    PRICE_SET = "PRICE_SET"
    # Stock
    STOCK_READ = "STOCK_READ"
    STOCK_VALUE_READ = "STOCK_VALUE_READ"
    STOCK_HISTORY_READ = "STOCK_HISTORY_READ"
    INVENTORY_MANAGE = "INVENTORY_MANAGE"
    STOCK_ADJUST = "STOCK_ADJUST"
    # Achats et fournisseurs
    PURCHASE_READ = "PURCHASE_READ"
    PURCHASE_WRITE = "PURCHASE_WRITE"
    PURCHASE_CANCEL = "PURCHASE_CANCEL"
    SUPPLIER_READ = "SUPPLIER_READ"
    SUPPLIER_MANAGE = "SUPPLIER_MANAGE"
    # Déplacements de stock (Lot 2)
    TRANSFER_READ = "TRANSFER_READ"
    TRANSFER_WRITE = "TRANSFER_WRITE"
    TRANSFER_CANCEL = "TRANSFER_CANCEL"
    # Ventes
    SALE_CREATE = "SALE_CREATE"
    SALE_READ = "SALE_READ"
    SALE_UPDATE = "SALE_UPDATE"
    SALE_CANCEL = "SALE_CANCEL"
    SALE_RETURN = "SALE_RETURN"
    SALE_ERROR_REPORT = "SALE_ERROR_REPORT"
    SALE_BELOW_MIN = "SALE_BELOW_MIN"
    PRICE_REQUEST_CREATE = "PRICE_REQUEST_CREATE"
    PRICE_REQUEST_READ = "PRICE_REQUEST_READ"
    PRICE_REQUEST_DECIDE = "PRICE_REQUEST_DECIDE"
    CUSTOMER_READ = "CUSTOMER_READ"
    CUSTOMER_MANAGE = "CUSTOMER_MANAGE"
    # Créances et versements
    RECEIVABLE_READ = "RECEIVABLE_READ"
    RECEIVABLE_CREATE = "RECEIVABLE_CREATE"
    RECEIVABLE_FOLLOW_UP = "RECEIVABLE_FOLLOW_UP"
    INSTALLMENT_CREATE = "INSTALLMENT_CREATE"
    INSTALLMENT_CANCEL = "INSTALLMENT_CANCEL"
    RECEIVABLE_WRITE_OFF = "RECEIVABLE_WRITE_OFF"
    # Dépenses
    EXPENSE_READ = "EXPENSE_READ"
    EXPENSE_CREATE = "EXPENSE_CREATE"
    EXPENSE_CORRECT = "EXPENSE_CORRECT"
    EXPENSE_CATEGORY_MANAGE = "EXPENSE_CATEGORY_MANAGE"
    TAG_READ = "TAG_READ"
    TAG_MERGE = "TAG_MERGE"
    # Transport (Lot 2)
    FLEET_READ = "FLEET_READ"
    FLEET_NAMES_READ = "FLEET_NAMES_READ"
    FLEET_MANAGE = "FLEET_MANAGE"
    TRIP_READ = "TRIP_READ"
    TRIP_MANAGE = "TRIP_MANAGE"
    TRIP_STEP_RECORD = "TRIP_STEP_RECORD"
    TRIP_EXPENSE_RECORD = "TRIP_EXPENSE_RECORD"
    TRIP_EXPENSE_VALIDATE = "TRIP_EXPENSE_VALIDATE"
    PAYROLL_READ = "PAYROLL_READ"
    PAYROLL_MANAGE = "PAYROLL_MANAGE"
    # Tableau de bord, accueils, alertes
    DASHBOARD_READ = "DASHBOARD_READ"
    HOME_READ = "HOME_READ"
    ALERT_READ = "ALERT_READ"
    # Import Excel (Lot 3)
    IMPORT_ARTICLES = "IMPORT_ARTICLES"
    IMPORT_STOCK = "IMPORT_STOCK"
    IMPORT_SUPPLIERS = "IMPORT_SUPPLIERS"
    IMPORT_CUSTOMERS = "IMPORT_CUSTOMERS"
    IMPORT_RECEIVABLES = "IMPORT_RECEIVABLES"
    IMPORT_FLEET = "IMPORT_FLEET"
    IMPORT_CANCEL = "IMPORT_CANCEL"
    # Journal et champs filtrés par les présentateurs
    AUDIT_READ = "AUDIT_READ"
    COST_READ = "COST_READ"
    SALES_DATA_READ = "SALES_DATA_READ"
    PRICE_READ = "PRICE_READ"
    SELLING_PRICE_READ = "SELLING_PRICE_READ"

    @property
    def mode(self) -> Mode:
        return Mode.READ if self in READ_PERMISSIONS else Mode.WRITE


READ_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.LOCATION_READ,
        Permission.STOCK_READ,
        Permission.STOCK_VALUE_READ,
        Permission.STOCK_HISTORY_READ,
        Permission.PURCHASE_READ,
        Permission.SUPPLIER_READ,
        Permission.TRANSFER_READ,
        Permission.SALE_READ,
        Permission.PRICE_REQUEST_READ,
        Permission.CUSTOMER_READ,
        Permission.RECEIVABLE_READ,
        Permission.EXPENSE_READ,
        Permission.TAG_READ,
        Permission.FLEET_READ,
        Permission.FLEET_NAMES_READ,
        Permission.TRIP_READ,
        Permission.PAYROLL_READ,
        Permission.DASHBOARD_READ,
        Permission.HOME_READ,
        Permission.ALERT_READ,
        Permission.AUDIT_READ,
        Permission.COST_READ,
        Permission.SALES_DATA_READ,
        Permission.PRICE_READ,
        Permission.SELLING_PRICE_READ,
    }
)
"""Permissions de consultation ; toutes les autres modifient des données."""

FIELD_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.COST_READ,  # prix d'achat, CMP, marge, valeur du stock (RG-D02)
        Permission.SALES_DATA_READ,  # ventes, clients, créances, chiffre d'affaires (RG-D03)
        Permission.PRICE_READ,  # tout prix ou montant de marchandise (RG-D05)
        Permission.SELLING_PRICE_READ,  # prix de vente de base et minimum (Q-14)
        Permission.AUDIT_READ,  # auteurs, historique avant/après (module 16)
    }
)
"""Permissions de champ, seules admises par `Policy.can_read_field`."""
