"""Fabrique de l'application FastAPI (adaptateur HTTP entrant).

Ne connaît aucun adaptateur concret : `bootstrap.container` lui fournit ses dépendances.
"""

from fastapi import FastAPI

from app.interface.http.config import HttpConfig
from app.interface.http.errors import register_error_handlers
from app.interface.http.routes import health
from app.interface.http.routes.attachment_components import AttachmentsComponents
from app.interface.http.routes.attachments import build_attachments_router
from app.interface.http.routes.auth import AuthComponents, build_auth_router
from app.interface.http.routes.catalog import CatalogComponents, build_catalog_router
from app.interface.http.routes.customers import build_customers_router
from app.interface.http.routes.expense_components import ExpensesComponents
from app.interface.http.routes.expense_settings import build_expense_settings_router
from app.interface.http.routes.expenses import build_expenses_router
from app.interface.http.routes.installments import build_installments_router
from app.interface.http.routes.inventories import build_inventories_router
from app.interface.http.routes.journal import JournalComponents, build_journal_router
from app.interface.http.routes.members import build_members_router
from app.interface.http.routes.places import build_places_router
from app.interface.http.routes.platform import build_platform_router
from app.interface.http.routes.purchases import build_purchases_router
from app.interface.http.routes.purchasing_components import PurchasingComponents
from app.interface.http.routes.receivables import build_receivables_router
from app.interface.http.routes.receivables_components import ReceivablesComponents
from app.interface.http.routes.reporting import ReportingComponents, build_reporting_router
from app.interface.http.routes.sales import build_sales_router
from app.interface.http.routes.sales_components import SalesComponents
from app.interface.http.routes.sales_returns import build_sales_returns_router
from app.interface.http.routes.shop_components import ShopsComponents
from app.interface.http.routes.shop_profile import build_shop_profile_router
from app.interface.http.routes.stock import build_stock_router
from app.interface.http.routes.stock_components import StockComponents
from app.interface.http.routes.suppliers import build_suppliers_router
from app.interface.http.routes.sync import build_sync_router
from app.interface.http.routes.sync_components import SyncComponents


def create_app(
    config: HttpConfig,
    auth: AuthComponents,
    journal: JournalComponents | None = None,
    shops: ShopsComponents | None = None,
    catalog: CatalogComponents | None = None,
    expenses: ExpensesComponents | None = None,
    stock: StockComponents | None = None,
    purchasing: PurchasingComponents | None = None,
    sales: SalesComponents | None = None,
    receivables: ReceivablesComponents | None = None,
    reporting: ReportingComponents | None = None,
    sync: SyncComponents | None = None,
    attachments: AttachmentsComponents | None = None,
) -> FastAPI:
    """`journal`/`shops` absents : leurs routes ne sont pas montées (outils, tests ciblés)."""
    prefix = config.api_prefix
    expose_docs = config.expose_docs
    app = FastAPI(
        title="Gestion de boutiques",
        version="0.1.0",
        openapi_url=f"{prefix}/openapi.json" if expose_docs else None,
        docs_url=f"{prefix}/docs" if expose_docs else None,
        redoc_url=None,
    )
    register_error_handlers(app, None if journal is None else journal.record_access_denied.execute)
    app.include_router(health.router, prefix=prefix)
    app.include_router(build_auth_router(auth, prefix), prefix=prefix)
    if journal is not None:
        app.include_router(build_journal_router(journal), prefix=prefix)
    if shops is not None:
        for build in (
            build_platform_router,
            build_shop_profile_router,
            build_places_router,
            build_members_router,
        ):
            app.include_router(build(shops), prefix=prefix)
    if catalog is not None:
        app.include_router(build_catalog_router(catalog), prefix=prefix)
    if expenses is not None:
        app.include_router(build_expenses_router(expenses), prefix=prefix)
        app.include_router(build_expense_settings_router(expenses), prefix=prefix)
    if stock is not None:
        app.include_router(build_stock_router(stock), prefix=prefix)
        app.include_router(build_inventories_router(stock), prefix=prefix)
    if purchasing is not None:
        app.include_router(build_suppliers_router(purchasing), prefix=prefix)
        app.include_router(build_purchases_router(purchasing), prefix=prefix)
    if sales is not None:
        app.include_router(build_sales_router(sales), prefix=prefix)
        app.include_router(build_customers_router(sales), prefix=prefix)
        app.include_router(build_sales_returns_router(sales), prefix=prefix)
    if receivables is not None:
        app.include_router(build_receivables_router(receivables), prefix=prefix)
        app.include_router(build_installments_router(receivables), prefix=prefix)
    if reporting is not None:
        app.include_router(build_reporting_router(reporting), prefix=prefix)
    if sync is not None:
        app.include_router(build_sync_router(sync), prefix=prefix)
    if attachments is not None:
        app.include_router(build_attachments_router(attachments, prefix), prefix=prefix)
    return app
