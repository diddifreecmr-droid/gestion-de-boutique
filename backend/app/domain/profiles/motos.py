"""Profil « Motos et camions » (CDC § 17), complet au Lot 1.

- Lieux : Garoua-Boulaï (entrepôt), Ngaoundéré (entrepôt), Garoua (boutique, seul point de
  vente). Réception des achats par défaut : **Garoua** au Lot 1 (décision Q-01 : pas de
  déplacement avant le Lot 2) ; le CDC § 17.1 prévoit Garoua-Boulaï à partir du Lot 2.
- Tous les modules disponibles à l'ouverture (Transferts, Transport, Import : à venir, specs
  § 15.1) ; reçu 80 mm (`thermal-80`) ; unité : la moto.
"""

from types import MappingProxyType

from app.domain.profiles import defaults as d
from app.domain.profiles.fields import FieldKind, FieldSpec
from app.domain.profiles.menus import entry, menu
from app.domain.profiles.modules import ALL_MODULES, AVAILABLE_MODULES, Module
from app.domain.profiles.printing import ReceiptFormat
from app.domain.profiles.profile import (
    LocationTemplate,
    ProfileCode,
    SettingsDefaults,
    ShopProfile,
)
from app.domain.shared.quantity import StockUnit
from app.domain.shared.roles import Role
from app.domain.shops.values import LocationKind

GAROUA = "Garoua"

M = Module  # abréviation des tables de menus ci-dessous

_MENUS = {
    Role.OWNER: menu(
        entry("home", "Accueil", M.DASHBOARD),
        entry("sales", "Ventes", M.SALES),
        entry("stock", "Stock", M.CATALOG),
        entry("trucks", "Camions", M.TRANSPORT),
        entry(
            "more",
            "Plus",
            M.CORE,
            entry("receivables", "Créances", M.RECEIVABLES),
            entry("purchases", "Achats", M.PURCHASES),
            entry("expenses", "Dépenses", M.EXPENSES),
            entry("customers", "Clients", M.SALES),
            entry("payroll", "Paie", M.TRANSPORT),
            entry("audit", "Journal", M.AUDIT),
            entry("settings", "Réglages", M.CORE),
        ),
    ),
    Role.SELLER: menu(
        entry("home", "Accueil", M.DASHBOARD),
        entry("new_sale", "Nouvelle vente", M.SALES),
        entry("my_sales", "Mes ventes", M.SALES),
        entry("receivables", "Créances", M.RECEIVABLES),
        entry("stock", "Stock", M.CATALOG),
    ),
    Role.ACCOUNTANT: menu(
        entry("home", "Accueil", M.DASHBOARD),
        entry("purchases", "Achats", M.PURCHASES),
        entry("stock", "Stock", M.CATALOG),
        entry("transfers", "Déplacements", M.TRANSFERS),
        entry("expenses", "Dépenses", M.EXPENSES),
    ),
    Role.DRIVER: menu(
        entry("my_trip", "Mon voyage", M.TRANSPORT),
        entry("my_trip_expenses", "Mes dépenses", M.TRANSPORT),
        entry("my_trips", "Mes voyages", M.TRANSPORT),
    ),
}

MOTOS = ShopProfile(
    code=ProfileCode.MOTOS,
    version=1,
    label="Motos et camions",
    modules=AVAILABLE_MODULES,
    available_modules=ALL_MODULES,
    roles=(Role.OWNER, Role.SELLER, Role.ACCOUNTANT, Role.DRIVER),
    role_labels=MappingProxyType(dict(d.SELLER_LABELS)),
    menus=MappingProxyType(_MENUS),
    article_fields=(
        FieldSpec("brand", "Marque", FieldKind.TEXT, required=True),
        FieldSpec("model", "Modèle", FieldKind.TEXT, required=True),
        FieldSpec("engine_cc", "Cylindrée (cm³)", FieldKind.INTEGER),
        d.CATEGORY,
    ),
    sale_fields=(
        d.COLOR,
        FieldSpec("chassis_number", "Numéro de châssis", FieldKind.TEXT, unique=True),
        FieldSpec("engine_number", "Numéro de moteur", FieldKind.TEXT),
    ),
    stock_units=(StockUnit.UNIT,),
    locations=(
        LocationTemplate("Garoua-Boulaï", LocationKind.WAREHOUSE, False, "Garoua-Boulaï", 1),
        LocationTemplate("Ngaoundéré", LocationKind.WAREHOUSE, False, "Ngaoundéré", 2),
        LocationTemplate(GAROUA, LocationKind.STORE, True, GAROUA, 3),
    ),
    reception_location=GAROUA,
    expense_categories=d.EXPENSE_CATEGORIES,
    payment_modes=d.PAYMENT_MODES,
    settings=SettingsDefaults(receipt_format=ReceiptFormat.MM80, truck_silent_hours=24),
)
