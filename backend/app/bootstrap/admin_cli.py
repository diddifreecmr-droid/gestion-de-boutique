"""Création de l'administrateur plateforme (premier démarrage en production, T25).

`tools/` n'est pas dans l'image de production : cette commande vit dans `app/` pour être
lancée depuis la console du conteneur `api` (Portainer → Console) :

    python -m app.bootstrap.admin_cli --phone 699000000 --name "Administrateur"

Le mot de passe (10 caractères au moins, politique de `validate_new_password`, specs § 15.1)
est demandé deux fois au clavier, ou lu sur une ligne de l'entrée standard si elle n'est pas un
terminal. Il n'est jamais passé en argument (il resterait dans l'historique et `ps`).

Fail-fast : numéro illisible, mot de passe faible, confirmation différente ou numéro déjà
inscrit arrêtent la commande avec un message explicite (code de sortie 1) ; rien n'est écrit.
"""

import argparse
import getpass
import sys
from collections.abc import Callable, Sequence

from app.bootstrap.config import load_settings
from app.bootstrap.identity import IdentityModule, build_identity
from app.domain.identity.credentials import validate_new_password
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.user import User
from app.domain.shared.errors import DomainError
from app.domain.shared.ids import UserId

PasswordReader = Callable[[], str]


class AdminCreationRefused(RuntimeError):
    """Création refusée (numéro pris, mot de passe faible ou non confirmé)."""


def create_platform_admin(
    identity: IdentityModule, *, phone: str, name: str, password: str
) -> UserId:
    parsed = PhoneNumber.parse(phone)
    try:
        validate_new_password(password, parsed)
    except DomainError as exc:
        msg = f"Mot de passe refusé : {exc.details.get('reason')} (10 caractères au moins)"
        raise AdminCreationRefused(msg) from exc
    with identity.uow_factory() as uow:
        if uow.users.find_by_phone(parsed) is not None:
            msg = f"Le numéro {parsed} est déjà inscrit : aucun compte créé"
            raise AdminCreationRefused(msg)
        admin = User.register(
            phone=parsed,
            name=name,
            secret_hash=identity.hasher.hash(password),
            is_platform_admin=True,
            must_change_pin=False,  # mot de passe choisi par l'administrateur lui-même
        )
        uow.users.add(admin)
        uow.commit()
    return admin.id


def read_password_interactively() -> str:
    """Deux saisies masquées (terminal) ; une ligne de l'entrée standard sinon."""
    if not sys.stdin.isatty():
        # Fin de ligne Windows et marque d'ordre d'octets (tube PowerShell 5) retirées.
        return sys.stdin.readline().rstrip("\r\n").removeprefix("﻿")
    first = getpass.getpass("Mot de passe de l'administrateur : ")
    if getpass.getpass("Confirmer le mot de passe : ") != first:
        msg = "Les deux saisies diffèrent : aucun compte créé"
        raise AdminCreationRefused(msg)
    return first


def main(
    argv: Sequence[str] | None = None, read_password: PasswordReader = read_password_interactively
) -> int:
    parser = argparse.ArgumentParser(description="Crée l'administrateur plateforme.")
    parser.add_argument("--phone", required=True, help="numéro de téléphone (ex. 699000000)")
    parser.add_argument("--name", required=True, help="nom affiché")
    args = parser.parse_args(argv)
    identity = build_identity(load_settings())
    try:
        user_id = create_platform_admin(
            identity, phone=args.phone, name=args.name, password=read_password()
        )
    except (AdminCreationRefused, DomainError) as exc:
        print(f"Échec : {exc}", file=sys.stderr)
        return 1
    print(f"Administrateur plateforme créé : {user_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
