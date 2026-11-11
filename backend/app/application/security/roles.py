"""Rôles d'un membre dans une boutique (CDC § 4.1) — réexport du domaine.

La définition vit dans `app.domain.shared.roles` depuis T10 (le rattachement et les profils de
boutique, dans le domaine, doivent la nommer). `Role` est le **même** objet : rien ne change pour
les appelants de la couche application.
"""

from app.domain.shared.roles import Role

__all__ = ["Role"]
