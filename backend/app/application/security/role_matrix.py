"""Traduction littérale de la matrice des droits du CDC § 4.2 (specs § 8.2).

Chaque bloc reprend, en commentaire, le libellé exact d'une ligne du CDC puis ses cellules
(Propriétaire | Vendeur | Comptable | Chauffeur). Les colonnes du code suivent cet ordre :
`_r(propriétaire, vendeur, comptable, chauffeur)`. Une ligne « gérer » est découpée en une
permission de lecture et une ou plusieurs d'écriture (« Lecture » → `READ` sur la lecture,
`NONE` sur l'écriture). Les permissions issues d'un cas d'utilisation sans ligne propre sont
rattachées à la ligne la plus proche et la source est citée.

Ambiguïtés (plan de recette § 6) : on retient l'interprétation **la plus restrictive** cohérente
avec le CDC ; elles sont marquées `[Q-xx]`. Les règles temporelles (« le jour même »,
« 7 jours ») relèvent des cas d'utilisation, pas de la matrice.
"""

from collections.abc import Mapping
from types import MappingProxyType

from app.application.security.access import Access
from app.application.security.permissions import Mode, Permission
from app.application.security.roles import Role

# Lettres du CDC : T = « Tout », S = « Siens », L = « Lecture », N = « — ».
T, S, L, N = Access.ALL, Access.OWN, Access.READ, Access.NONE
P = Permission


def _r(owner: Access, seller: Access, accountant: Access, driver: Access) -> Mapping[Role, Access]:
    return MappingProxyType(
        {Role.OWNER: owner, Role.SELLER: seller, Role.ACCOUNTANT: accountant, Role.DRIVER: driver}
    )


_MATRIX: dict[Permission, Mapping[Role, Access]] = {
    # « Gérer les utilisateurs et les réglages de la boutique » : Tout | — | — | —
    # (inclut la déconnexion à distance RG-D07 et les modes de paiement)
    P.MEMBER_MANAGE: _r(T, N, N, N),
    P.SETTINGS_MANAGE: _r(T, N, N, N),
    # « Gérer les lieux (boutique, entrepôts) » : Tout | — | Lecture | —
    # [Q-30] le vendeur ne lit pas la liste des lieux ; le stock par lieu passe par STOCK_READ.
    P.LOCATION_READ: _r(T, N, L, N),
    P.LOCATION_MANAGE: _r(T, N, N, N),
    # « Créer et modifier un article » : Tout | — | Oui, sans le prix de vente | —
    # « sans le prix de vente » = PRICE_SET et SELLING_PRICE_READ refusés au comptable.
    P.ARTICLE_WRITE: _r(T, N, T, N),
    # UC-STK-04 « Archiver ou réactiver un article » : Propriétaire seul.
    P.ARTICLE_ARCHIVE: _r(T, N, N, N),
    # « Fixer le prix de vente de base et le prix minimum » : Tout | — | — | —
    P.PRICE_SET: _r(T, N, N, N),
    # [Q-14] le comptable ne voit pas non plus le prix de base ni le minimum.
    P.SELLING_PRICE_READ: _r(T, L, N, N),
    # « Voir le stock disponible (quantités) » : Tout | Lecture | Tout | —
    P.STOCK_READ: _r(T, L, T, N),
    # « Voir les prix d'achat et la valeur du stock » : Tout | — | Tout | —
    # COST_READ (champ) couvre prix d'achat, CMP, marge et valeur (RG-D02) ; l'historique
    # d'article UC-STK-06 (Propriétaire, Comptable) expose des coûts : même ligne.
    P.COST_READ: _r(T, N, T, N),
    P.STOCK_VALUE_READ: _r(T, N, T, N),
    P.STOCK_HISTORY_READ: _r(T, N, T, N),
    # « Faire un inventaire, un ajustement de stock » : Tout | — | Tout | —
    P.INVENTORY_MANAGE: _r(T, N, T, N),
    P.STOCK_ADJUST: _r(T, N, T, N),
    # « Enregistrer un achat, gérer les fournisseurs » : Tout | — | Tout | —
    # PURCHASE_WRITE = saisie, correction (7 jours pour le comptable, UC-ACH-03), paiement.
    P.PURCHASE_READ: _r(T, N, T, N),
    P.PURCHASE_WRITE: _r(T, N, T, N),
    # [Q-13] UC-ACH-04 « Annuler un achat » : Propriétaire seul, malgré « Tout ».
    P.PURCHASE_CANCEL: _r(T, N, N, N),
    P.SUPPLIER_READ: _r(T, N, T, N),
    P.SUPPLIER_MANAGE: _r(T, N, T, N),
    # « Créer et réceptionner un déplacement de stock » : Tout | — | Tout | —   (Lot 2)
    P.TRANSFER_READ: _r(T, N, T, N),
    P.TRANSFER_WRITE: _r(T, N, T, N),
    # UC-TRF-04 : Comptable « son propre déplacement, le jour même ».
    P.TRANSFER_CANCEL: _r(T, N, S, N),
    # « Enregistrer une vente » : Tout | Oui | — | —
    # « Oui » du vendeur = une vente attribuée à lui-même (seller_id = acteur) : OWN.
    P.SALE_CREATE: _r(T, S, N, N),
    # « Voir les ventes » : Tout | Siens | — | —
    P.SALE_READ: _r(T, S, N, N),
    # RG-D03 : ventes, clients, créances, chiffre d'affaires — jamais pour le comptable.
    P.SALES_DATA_READ: _r(T, S, N, N),
    # « Modifier ou annuler une vente, faire un retour » : Tout | Signaler une erreur | — | —
    P.SALE_UPDATE: _r(T, N, N, N),
    P.SALE_CANCEL: _r(T, N, N, N),
    P.SALE_RETURN: _r(T, N, N, N),
    # UC-PAP-01 « Échange » [QC-4] : Propriétaire Tout (délai dépassable, journal sensible) ;
    # Vendeur Siens **si** le réglage `employee_exchange_allowed` est vrai et dans le délai
    # `exchange_days` (contrôlés par le cas d'utilisation, `sales/exchange_rights.py`).
    P.SALE_EXCHANGE: _r(T, S, N, N),
    # [Q-32] « Tout » : le propriétaire peut aussi signaler (aligné sur la recette M15).
    P.SALE_ERROR_REPORT: _r(T, S, N, N),
    # « Vendre au-dessous du prix minimum » : Tout | — | — | —
    # UC-VEN-03 : le vendeur demande (ses demandes), le propriétaire décide.
    P.SALE_BELOW_MIN: _r(T, N, N, N),
    P.PRICE_REQUEST_CREATE: _r(T, S, N, N),
    P.PRICE_REQUEST_READ: _r(T, S, N, N),
    P.PRICE_REQUEST_DECIDE: _r(T, N, N, N),
    # « Créer et voir les créances » : Tout | Siens | — | —
    # [Q-21] « Siens » = créances dont il est le vendeur responsable (responsible_seller_id).
    P.RECEIVABLE_READ: _r(T, S, N, N),
    # [Q-15] créance ancienne UC-CRE-02 : Propriétaire seul ; la créance d'une vente à
    # crédit naît de SALE_CREATE (UC-CRE-01, automatique).
    P.RECEIVABLE_CREATE: _r(T, N, N, N),
    # UC-CRE-06/07 rappel, garant, pièce : Propriétaire, Vendeur (ses créances).
    P.RECEIVABLE_FOLLOW_UP: _r(T, S, N, N),
    # UC-VEN-11 / UC-CRE-05 « Gérer les clients » : Vendeur (ses clients), Propriétaire.
    P.CUSTOMER_READ: _r(T, S, N, N),
    P.CUSTOMER_MANAGE: _r(T, S, N, N),
    # « Enregistrer un versement » : Tout | Pour ses clients | — | —
    P.INSTALLMENT_CREATE: _r(T, S, N, N),
    # « Annuler un versement, passer une créance en perte » : Tout | — | — | —
    P.INSTALLMENT_CANCEL: _r(T, N, N, N),
    P.RECEIVABLE_WRITE_OFF: _r(T, N, N, N),
    # « Enregistrer une dépense journalière » : Tout | — | Tout | —
    P.EXPENSE_READ: _r(T, N, T, N),
    P.EXPENSE_CREATE: _r(T, N, T, N),
    # [Q-11] UC-DEP-04 « Auteur (le jour même), Propriétaire (toujours) » : le comptable ne
    # corrige que ses propres dépenses ; le délai est contrôlé par le cas d'utilisation.
    P.EXPENSE_CORRECT: _r(T, N, S, N),
    # UC-DEP-02 : catégories et fusion des tags par le propriétaire ; tags lus à la saisie.
    P.EXPENSE_CATEGORY_MANAGE: _r(T, N, N, N),
    P.TAG_READ: _r(T, N, T, N),
    P.TAG_MERGE: _r(T, N, N, N),
    # « Gérer camions et chauffeurs » : Tout | — | Liste des noms seulement (pour un
    # déplacement) | —   (Lot 2 ; RG-D04 : ni voyages, ni dépenses de route, ni paie)
    P.FLEET_READ: _r(T, N, N, N),
    P.FLEET_NAMES_READ: _r(T, N, L, N),
    P.FLEET_MANAGE: _r(T, N, N, N),
    # « Créer, suivre et clôturer un voyage » : Tout | — | — | Ses voyages (suivi seulement)
    P.TRIP_READ: _r(T, N, N, S),
    P.TRIP_MANAGE: _r(T, N, N, N),
    # « Saisir une étape ou une dépense de voyage » : Tout | — | — | Ses voyages
    P.TRIP_STEP_RECORD: _r(T, N, N, S),
    P.TRIP_EXPENSE_RECORD: _r(T, N, N, S),
    # « Valider une dépense de voyage » : Tout | — | — | —
    P.TRIP_EXPENSE_VALIDATE: _r(T, N, N, N),
    # « Primes, avances et paie des chauffeurs » : Tout | — | — | —  (UC-TRA-10 : le
    # chauffeur ne voit pas sa paie)
    P.PAYROLL_READ: _r(T, N, N, N),
    P.PAYROLL_MANAGE: _r(T, N, N, N),
    # RG-D05 / UC-TRA-10 : le chauffeur ne voit aucun prix de marchandise.
    P.PRICE_READ: _r(T, L, L, N),
    # « Tableau de bord complet (ventes, encaissé, marges) » : Tout | — | — | —
    P.DASHBOARD_READ: _r(T, N, N, N),
    # UC-TDB-05 accueil de son rôle et UC-SOC-09 alertes : « Tous », chacun les siens ; le
    # contenu reste filtré par les autres permissions.
    P.HOME_READ: _r(T, S, S, S),
    P.ALERT_READ: _r(T, S, S, S),
    # « Importer depuis Excel » : Tout | — | Articles, stock, fournisseurs | —   (Lot 3)
    P.IMPORT_ARTICLES: _r(T, N, T, N),
    P.IMPORT_STOCK: _r(T, N, T, N),
    P.IMPORT_SUPPLIERS: _r(T, N, T, N),
    P.IMPORT_CUSTOMERS: _r(T, N, N, N),
    P.IMPORT_RECEIVABLES: _r(T, N, N, N),
    P.IMPORT_FLEET: _r(T, N, N, N),
    # UC-IMP-03 « Annuler un import » : Propriétaire.
    P.IMPORT_CANCEL: _r(T, N, N, N),
    # « Journal d'actions » : Tout | — | — | —
    P.AUDIT_READ: _r(T, N, N, N),
}


def validate_matrix(
    matrix: Mapping[Permission, Mapping[Role, Access]],
) -> Mapping[Permission, Mapping[Role, Access]]:
    """Échoue à l'import si une cellule manque ou si « Lecture » vise une écriture."""
    missing = set(Permission) - matrix.keys()
    if missing:
        msg = f"Matrice des droits incomplète : {sorted(missing)}"
        raise RuntimeError(msg)
    for permission, cells in matrix.items():
        if set(cells) != set(Role):
            msg = f"{permission} : chaque rôle doit avoir une cellule"
            raise RuntimeError(msg)
        if permission.mode is Mode.WRITE and Access.READ in cells.values():
            msg = f"{permission} : « Lecture » n'a pas de sens sur une permission d'écriture"
            raise RuntimeError(msg)
    return MappingProxyType(dict(matrix))


ROLE_MATRIX: Mapping[Permission, Mapping[Role, Access]] = validate_matrix(_MATRIX)
"""Matrice immuable, complète et cohérente (vérifiée au chargement du module)."""


def access_for(role: Role, permission: Permission) -> Access:
    return ROLE_MATRIX[permission][role]
