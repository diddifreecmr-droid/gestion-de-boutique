"""Jeu de démonstration (T-démo) : `python -m app.bootstrap.seed_demo --admin-phone 699000000`.

Dans `app/` (et non `tools/`) pour être lancé depuis la console du conteneur `api` de
production. Crée « Démo Motos », « Démo Prêt-à-porter » et « Démo Tissus » par les cas
d'utilisation (journal, numérotation, stock, CMP, alertes cohérents), datées sur les 10
derniers jours par une horloge rejouée (`services.ReplayClock`, injectée dans `build_core`).
Idempotent : une boutique déjà présente (même nom) est laissée telle quelle.

`--dry-run` : lit seulement les noms des boutiques existantes, puis joue tout le scénario sur
une base **mémoire** jetable (avec un administrateur jetable) : rien n'est écrit en base.

Affiche à la fin : boutique, rôle, nom, téléphone, code provisoire (à changer à la 1re
connexion). Échec (administrateur absent, règle métier refusée) : message, code de sortie 1.
"""

import argparse
import secrets
import sys
from collections.abc import Sequence

from app.application.identity.ports import PasswordHasher
from app.bootstrap.admin_cli import create_platform_admin
from app.bootstrap.config import PersistenceBackend, Settings, load_settings
from app.bootstrap.core import build_core
from app.bootstrap.identity import IdentityModule, build_identity
from app.bootstrap.seed_demo.seed import DemoReport, DemoSeedRefused, seed_demo
from app.bootstrap.seed_demo.services import ReplayClock
from app.domain.shared.errors import DomainError
from app.infrastructure.persistence.sqlalchemy.startup import verify_database
from app.infrastructure.system_clock import SystemClock


def _identity(settings: Settings, hasher: PasswordHasher | None) -> IdentityModule:
    core = build_core(settings, ReplayClock(SystemClock().now()))
    if core.engine is not None:
        verify_database(core.engine)
    return build_identity(settings, hasher=hasher, core=core)


def run(
    settings: Settings, admin_phone: str, *, dry_run: bool, hasher: PasswordHasher | None = None
) -> DemoReport:
    target = _identity(settings, hasher)
    if not dry_run:
        return seed_demo(target, admin_phone)
    existing = frozenset(summary.name for summary in target.core.catalog.list_all())
    memory = settings.model_copy(update={"PERSISTENCE_BACKEND": PersistenceBackend.MEMORY})
    scratch = _identity(memory, hasher)
    password = f"Sim-{secrets.token_urlsafe(12)}"
    create_platform_admin(scratch, phone=admin_phone, name="Simulation", password=password)
    return seed_demo(scratch, admin_phone, skip=existing)


def print_report(report: DemoReport, *, dry_run: bool) -> None:
    if dry_run:
        print("Simulation (--dry-run) : rien n'a été écrit en base.")
    for name in report.created:
        print(f"Boutique « {name} » {'serait créée' if dry_run else 'créée'}")
    for name in report.skipped:
        print(f"Boutique « {name} » déjà présente : laissée telle quelle")
    print(f"{report.sales} ventes de démonstration")
    header = ("Boutique", "Rôle", "Nom", "Téléphone", "Code provisoire")
    table = [header, *((r.shop, r.role, r.name, r.phone, r.code) for r in report.rows)]
    widths = [max(len(row[i]) for row in table) for i in range(len(header))]
    for row in table:
        print("  ".join(c.ljust(w) for c, w in zip(row, widths, strict=True)).rstrip())
    print("Chaque compte devra changer son code à la première connexion.")


def main(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    hasher: PasswordHasher | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="Crée les trois boutiques de démonstration.")
    parser.add_argument("--admin-phone", required=True, help="administrateur plateforme existant")
    parser.add_argument("--dry-run", action="store_true", help="simule sans rien écrire")
    args = parser.parse_args(argv)
    try:
        report = run(
            settings or load_settings(), args.admin_phone, dry_run=args.dry_run, hasher=hasher
        )
    except (DemoSeedRefused, DomainError) as exc:
        print(f"Échec : {exc}", file=sys.stderr)
        return 1
    print_report(report, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
