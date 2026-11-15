"""Profils « Prêt-à-porter » (CDC § 18) et « Textile » (CDC § 19) — **minimaux**, Lot 3.

Présents dès maintenant pour que l'ouverture d'une boutique et `GET /profile` ne supposent
jamais le profil Motos ; leurs cas d'utilisation propres (échanges, vente au mètre) arrivent au
Lot 3. Pas de Transport ni de Chauffeur ; Transferts inactif tant qu'aucune réserve n'existe ;
une boutique point de vente ; reçu 58 mm (`thermal-58`) ; délai d'échange 7 jours.

Décisions client du 2026-11-15 (version 2) : vente jamais refusée pour manque de stock, stock
réservé au gérant (pas de menu Stock pour le vendeur), Prêt-à-porter sans champ de vente
(un article = un nom + référence/SKU facultative + prix), Textile : tissu et couleur (un
article par couleur) et « rouleau » au lieu de « pièce ».
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

_AVAILABLE = ALL_MODULES - {Module.TRANSPORT}
_STORE = "Boutique"

M = Module  # abréviation des tables de menus ci-dessous

_MENUS = {
    Role.OWNER: menu(
        entry("home", "Accueil", M.CORE),
        entry("sales", "Ventes", M.SALES),
        entry("stock", "Stock", M.CATALOG),
        entry("receivables", "Créances", M.RECEIVABLES),
        entry(
            "more",
            "Plus",
            M.CORE,
            entry("purchases", "Achats", M.PURCHASES),
            entry("expenses", "Dépenses", M.EXPENSES),
            entry("customers", "Clients", M.SALES),
            entry("audit", "Journal", M.AUDIT),
            entry("import", "Import", M.IMPORT),
            entry("settings", "Réglages", M.CORE),
        ),
    ),
    Role.SELLER: menu(
        entry("home", "Accueil", M.CORE),
        entry("new_sale", "Nouvelle vente", M.SALES),
        entry("my_sales", "Mes ventes", M.SALES),
        entry("receivables", "Créances", M.RECEIVABLES),
    ),
    Role.ACCOUNTANT: menu(
        entry("home", "Accueil", M.CORE),
        entry("purchases", "Achats", M.PURCHASES),
        entry("stock", "Stock", M.CATALOG),
        entry("expenses", "Dépenses", M.EXPENSES),
        entry("inventory", "Inventaire", M.CATALOG),
    ),
}


def _apparel_like(
    code: ProfileCode,
    label: str,
    article_fields: tuple[FieldSpec, ...],
    sale_fields: tuple[FieldSpec, ...],
    stock_units: tuple[StockUnit, ...],
    piece_word: str = "pièce",
) -> ShopProfile:
    """Prêt-à-porter et textile partagent rôles, menus, lieux et réglages (CDC § 19 « idem »)."""
    return ShopProfile(
        code=code,
        version=2,
        sale_refused_without_stock=False,
        stock_reserved_to_owner=True,
        piece_word=piece_word,
        label=label,
        modules=_AVAILABLE & AVAILABLE_MODULES,
        available_modules=_AVAILABLE,
        roles=(Role.OWNER, Role.SELLER, Role.ACCOUNTANT),
        role_labels=MappingProxyType(dict(d.EMPLOYEE_LABELS)),
        menus=MappingProxyType(_MENUS),
        article_fields=article_fields,
        sale_fields=sale_fields,
        stock_units=stock_units,
        locations=(LocationTemplate(_STORE, LocationKind.STORE, True, None, 1),),
        reception_location=_STORE,
        expense_categories=d.EXPENSE_CATEGORIES,
        payment_modes=d.PAYMENT_MODES,
        settings=SettingsDefaults(receipt_format=ReceiptFormat.MM58, exchange_days=7),
    )


APPAREL = _apparel_like(
    ProfileCode.APPAREL,
    "Prêt-à-porter",
    (
        FieldSpec("name", "Nom", FieldKind.TEXT, required=True),
        d.REFERENCE,
        d.CATEGORY,
        FieldSpec("type", "Type", FieldKind.TEXT),
        FieldSpec("brand", "Marque", FieldKind.TEXT),
    ),
    (),  # simplifié (2026-11-15) : ni taille ni couleur à la vente, remplace les choix de T40
    (StockUnit.PIECE,),
)

TEXTILE = _apparel_like(
    ProfileCode.TEXTILE,
    "Textile",
    (
        FieldSpec("name", "Nom", FieldKind.TEXT, required=True),
        d.REFERENCE,
        FieldSpec("fabric", "Tissu", FieldKind.TEXT),
        d.COLOR,
        FieldSpec("type", "Type", FieldKind.TEXT),
        FieldSpec("unit", "Unité", FieldKind.CHOICE, required=True, choices=("METER", "PIECE")),
        FieldSpec("sold_by_piece", "Vente au rouleau", FieldKind.BOOLEAN),
        FieldSpec("piece_length_m", "Longueur du rouleau (m)", FieldKind.DECIMAL),
    ),
    (FieldSpec("length_m", "Longueur (m)", FieldKind.DECIMAL),),
    (StockUnit.METER, StockUnit.PIECE),
    piece_word="rouleau",
)
