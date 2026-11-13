"""DTO de reçu (UC-VEN-04, TR-18, RCP-01) : tout ce que le client imprime, **sans aucun coût
ni marge** quel que soit le rôle (SEC-N04). Le rendu (58 mm, 80 mm, A5/A4) est côté client."""

from datetime import datetime

from pydantic import BaseModel

from app.interface.http.schemas.sales import DetailResponse


class ReceiptHeader(BaseModel):
    shop_name: str
    city: str
    phone: str
    address: str | None
    niu: str | None
    rccm: str | None
    show_logo: bool


class ReceiptPrintSettings(BaseModel):
    receipt_format: str
    paper_width_mm: int
    printable_width_mm: int
    padding_mm: int
    """Marge du papier (réglage `margin_mm`), renommée : aucune clé « margin » sur un reçu."""
    font_size_pt: int
    copies: int


class ReceiptCustomer(BaseModel):
    name: str
    phone: str


class ReceiptLineResponse(BaseModel):
    article_name: str
    sale_mode: str
    quantity: str
    quantity_label: str
    """Quantité imprimée : « 2 », « 2,5 m », « 1 pièce (5,49 m) » (TEX-06)."""
    unit_price: int
    line_total: int
    details: list[DetailResponse]


class ReceiptPaymentResponse(BaseModel):
    mode_name: str
    amount: int
    reference: str | None


class ReceiptMention(BaseModel):
    code: str
    label: str


class SaleReceiptResponse(BaseModel):
    title: str
    header: ReceiptHeader
    sale_id: str
    number: str
    provisional_number: str | None
    sold_at: datetime
    seller_name: str
    customer: ReceiptCustomer | None
    lines: list[ReceiptLineResponse]
    total: int
    paid: int
    payments: list[ReceiptPaymentResponse]
    remaining: int
    mentions: list[ReceiptMention]
    footer_message: str | None
    printing: ReceiptPrintSettings
    print_sequence: int
    printed_at: datetime
