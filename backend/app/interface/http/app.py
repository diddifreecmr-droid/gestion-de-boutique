"""Fabrique de l'application FastAPI (adaptateur HTTP entrant).

Ne connaît aucun adaptateur concret : `bootstrap.container` lui fournit ses dépendances.
"""

from fastapi import FastAPI

from app.domain.profiles.modules import Module
from app.interface.http.config import HttpConfig
from app.interface.http.errors import register_error_handlers
from app.interface.http.modules import ShopRoutes, require_declared_modules
from app.interface.http.routes import health
from app.interface.http.routes.attachment_components import AttachmentsComponents
from app.interface.http.routes.attachments import build_attachments_router
from app.interface.http.routes.auth import AuthComponents, build_auth_router
from app.interface.http.routes.catalog import CatalogComponents, build_catalog_router
from app.interface.http.routes.customers import build_customers_router
from app.interface.http.routes.expense_components import ExpensesComponents
from app.interface.http.routes.expense_settings import build_expense_settings_router
from app.interface.http.routes.expenses import build_expenses_router
from app.interface.http.routes.import_components import ImportsComponents
from app.interface.http.routes.imports import build_imports_router
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
    imports: ImportsComponents | None = None,
) -> FastAPI:
    """`journal`/`shops` absents : leurs routes ne sont pas montées (outils, tests ciblés).

    Chaque routeur de boutique déclare son module (`ShopRoutes.include`, specs § 15.1).
    """
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
    shop = ShopRoutes(app, auth.guard, prefix)
    if journal is not None:
        shop.include(build_journal_router(journal), Module.AUDIT, {"/alerts": Module.CORE})
    if shops is not None:
        app.include_router(build_platform_router(shops), prefix=prefix)
        for build in (build_shop_profile_router, build_places_router, build_members_router):
            shop.include(build(shops), Module.CORE)
    if catalog is not None:
        shop.include(build_catalog_router(catalog, prefix), Module.CATALOG)
    if expenses is not None:
        shop.include(build_expenses_router(expenses), Module.EXPENSES)
        shop.include(build_expense_settings_router(expenses), Module.EXPENSES)
    if stock is not None:
        shop.include(build_stock_router(stock), Module.CATALOG)
        shop.include(build_inventories_router(stock), Module.CATALOG)
    if purchasing is not None:
        shop.include(build_suppliers_router(purchasing), Module.PURCHASES)
        shop.include(build_purchases_router(purchasing), Module.PURCHASES)
    if sales is not None:
        shop.include(build_sales_router(sales), Module.SALES)
        shop.include(build_customers_router(sales), Module.SALES)
        shop.include(build_sales_returns_router(sales), Module.SALES)
    if receivables is not None:
        shop.include(build_receivables_router(receivables), Module.RECEIVABLES)
        shop.include(build_installments_router(receivables), Module.RECEIVABLES)
    if reporting is not None:
        shop.include(build_reporting_router(reporting), Module.DASHBOARD, {"/home": Module.CORE})
    if sync is not None:
        shop.include(build_sync_router(sync), Module.CORE)
    if attachments is not None:
        shop.include(build_attachments_router(attachments, prefix), Module.CORE)
    if imports is not None:  # module à venir (T46) : éteint pour toute boutique
        shop.include(build_imports_router(imports), Module.IMPORT)
    require_declared_modules(app, prefix)
    return app
