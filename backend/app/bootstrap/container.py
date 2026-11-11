"""Composition root (specs § 4.1, règle 5) : seul module qui assemble les adaptateurs concrets.

Point d'entrée ASGI : `uvicorn app.bootstrap.container:build_app --factory`.
"""

import logging
from pathlib import Path

from fastapi import FastAPI

from app.bootstrap.catalog import build_catalog
from app.bootstrap.config import DEFAULT_ENV_FILE, Environment, Settings, load_settings
from app.bootstrap.core import build_core
from app.bootstrap.expenses import build_expenses
from app.bootstrap.identity import build_identity
from app.bootstrap.journal import build_journal
from app.bootstrap.purchasing import build_purchasing
from app.bootstrap.receivables import build_receivables
from app.bootstrap.reporting import build_reporting
from app.bootstrap.sales import build_sales, sales_ranking
from app.bootstrap.shops import build_shops
from app.bootstrap.stock import build_stock
from app.infrastructure.system_clock import SystemClock
from app.interface.http.app import create_app
from app.interface.http.config import HttpConfig

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(format=_LOG_FORMAT)
    logging.getLogger("app").setLevel(settings.LOG_LEVEL)


def http_config_from(settings: Settings) -> HttpConfig:
    """Traduit la configuration globale en configuration de l'adaptateur HTTP."""
    return HttpConfig(
        api_prefix=settings.API_PREFIX,
        expose_docs=settings.ENVIRONMENT is not Environment.PROD,
    )


def build_app(env_file: Path | None = DEFAULT_ENV_FILE) -> FastAPI:
    """Lit la configuration (fail-fast), configure la journalisation, assemble l'application."""
    settings = load_settings(env_file)
    configure_logging(settings)
    clock = SystemClock()
    core = build_core(settings, clock)
    identity = build_identity(settings, core=core)
    journal = build_journal(settings, clock=clock, guard=identity.auth.guard, core=core)
    shops = build_shops(identity)
    catalog = build_catalog(identity, ranking=sales_ranking(clock))
    expenses = build_expenses(identity)
    stock = build_stock(identity)
    purchasing = build_purchasing(identity, stock.ledger)
    sales = build_sales(identity, stock.ledger)
    receivables = build_receivables(identity)
    reporting = build_reporting(identity)
    app = create_app(
        http_config_from(settings),
        identity.auth,
        journal.http,
        shops.http,
        catalog=catalog.http,
        expenses=expenses.http,
        stock=stock.http,
        purchasing=purchasing.http,
        sales=sales.http,
        receivables=receivables.http,
        reporting=reporting.http,
    )
    # Fabrique des unités de travail de boutique (handlers du journal et des alertes branchés).
    app.state.uow_factory = journal.uow_factory
    app.state.journal = journal
    return app
