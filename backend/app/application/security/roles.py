"""Rôles d'un membre dans une boutique (CDC § 4.1).

Un utilisateur a **un seul rôle par boutique**. Le libellé affiché (« Vendeur » ou « Employé »
en prêt-à-porter et textile) dépend du profil de la boutique, pas d'ici : la valeur est un code
stable. L'administrateur plateforme n'est **pas** un rôle de boutique (voir `Actor`).
"""

from enum import StrEnum


class Role(StrEnum):
    """Code stable du rôle, relu à chaque requête depuis le rattachement (specs § 8.1)."""

    OWNER = "owner"
    """Propriétaire : super administrateur de sa boutique."""

    SELLER = "seller"
    """Vendeur (« Employé » selon le profil) : ses ventes, ses créances, le stock disponible."""

    ACCOUNTANT = "accountant"
    """Comptable : comptabilité matière (achats, stock, dépenses) ; ne voit aucune vente."""

    DRIVER = "driver"
    """Chauffeur : ses voyages seulement (profil Motos et camions)."""
