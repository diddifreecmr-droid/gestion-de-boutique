/**
 * Contrat des retours et échanges (UC-VEN-09, T16b) : alias **générés** de `schema.gen.ts`.
 * Montants en entiers FCFA, quantités en chaînes décimales. TR-05 : pour un vendeur, `margin`,
 * `margin_wac` (retour) et `cost`, `margin`, `margin_wac` (lignes) sont **absents** du JSON.
 */
import type { components } from "../api/schema.gen";

type Schemas = components["schemas"];

/** Corps de `POST /sales/{id}/returns` ; `id` (UUIDv7) rend l'envoi idempotent. */
export type SaleReturnCommand = Schemas["SaleReturnCreate"];
/** Ligne rendue : position (1 = première), quantité, état, châssis rendus. */
export type ReturnLineInput = Schemas["ReturnLineRequest"];
export type RefundInput = Schemas["RefundRequest"];
export type ExchangeInput = Schemas["ExchangeRequest"];
export type StockCondition = Schemas["StockCondition"];

export type SaleReturn = Schemas["SaleReturnResponse"];
export type ReturnedLine = Schemas["ReturnedLineResponse"];
/** `GET /sales/{id}/returns` : retours et, par ligne, vendu / rendu / encore rendable. */
export type SaleReturns = Schemas["SaleReturnsResponse"];
export type LineBalance = Schemas["LineBalanceResponse"];
