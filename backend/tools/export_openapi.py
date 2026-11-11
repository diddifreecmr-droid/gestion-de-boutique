"""Exporte le contrat OpenAPI de l'API dans `backend/openapi.json` (specs § 6.1 « Contrat »).

Le frontend génère ses types TypeScript à partir de ce fichier (`npm run gen:api`) ; il n'est
jamais écrit à la main. L'application est assemblée comme dans `bootstrap.container.build_app`
(noyau partagé, identité, journal et alertes, socle des boutiques : **toutes** les routes),
avec une configuration de test fixe et la persistance mémoire : le contrat ne dépend ni de
`.env`, ni du secret réel, ni de la base.

Usage (depuis `backend/`) : `uv run python -m tools.export_openapi [--check] [--output CHEMIN]`
Code de sortie : 0 si le fichier est écrit (ou à jour avec `--check`), 1 s'il est périmé.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import SecretStr

from app.bootstrap.config import Environment, PersistenceBackend, Settings
from app.bootstrap.container import http_config_from
from app.bootstrap.core import build_core
from app.bootstrap.identity import build_identity
from app.bootstrap.journal import build_journal
from app.bootstrap.shops import build_shops
from app.infrastructure.system_clock import SystemClock
from app.interface.http.app import create_app

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "openapi.json"
# Secret factice : il ne sert qu'à assembler l'application, il n'apparaît pas dans le contrat.
_EXPORT_JWT_SECRET = "export-openapi-secret-factice-0123456789abcdef"


def build_openapi_document() -> str:
    """Contrat sérialisé de façon stable (indentation 2, UTF-8, saut de ligne final)."""
    settings = Settings(
        ENVIRONMENT=Environment.TEST,
        JWT_SECRET=SecretStr(_EXPORT_JWT_SECRET),
        PERSISTENCE_BACKEND=PersistenceBackend.MEMORY,
        _env_file=None,
    )
    clock = SystemClock()
    core = build_core(settings, clock)
    identity = build_identity(settings, core=core)
    journal = build_journal(settings, clock=clock, guard=identity.auth.guard, core=core)
    shops = build_shops(identity)
    app = create_app(http_config_from(settings), identity.auth, journal.http, shops.http)
    schema = app.openapi()
    if not schema.get("paths"):
        msg = "Contrat OpenAPI vide : aucune route exportée"
        raise RuntimeError(msg)
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="échoue si le fichier est périmé")
    args = parser.parse_args(argv)
    output: Path = args.output
    document = build_openapi_document()
    if args.check:
        current = output.read_text(encoding="utf-8") if output.is_file() else None
        if current != document:
            print(f"{output} est périmé : relancez tools.export_openapi", file=sys.stderr)
            return 1
        print(f"OK : {output} est à jour.")
        return 0
    output.write_text(document, encoding="utf-8", newline="\n")
    print(f"Contrat OpenAPI écrit dans {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
