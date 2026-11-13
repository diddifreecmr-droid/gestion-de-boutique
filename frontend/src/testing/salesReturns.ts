/** Ventes de test des retours et ouverture de la fiche (tests seulement). */
import { screen } from "@testing-library/react";
import type { RecordSaleCommand } from "../core/gateways/salesContract";
import { SHOP_A } from "./fakeApi";
import { renderSale } from "./renderSale";
import { saleCommand } from "./salesFixtures";
import { addSale, type Routes, type SaleRole, type SaleServer } from "./salesServer";

/** Deux Haojue HJ125-8 à 780 000 au comptant, châssis LBX0001 et LBX0002. */
export const TWO_MOTOS = saleCommand({
  lines: [
    {
      article_id: "art-hj125-8",
      sale_mode: "unit",
      quantity: "2",
      unit_price: 780_000,
      details: [
        { color: "Rouge", chassis_number: "LBX0001", engine_number: null, size: null },
        { color: "Bleu", chassis_number: "LBX0002", engine_number: null, size: null },
      ],
    },
  ],
  payments: [{ mode_id: "pm-cash", amount: 1_560_000, reference: null }],
});

/** Une Haojue HJ125-8 à crédit : 200 000 versés, 580 000 dus. */
export const CREDIT_MOTO = saleCommand({
  kind: "credit",
  customer: { id: "cus-moussa", name: "Moussa Abdou", phone: "+237690000000", kind: "individual" },
  payments: [{ mode_id: "pm-cash", amount: 200_000, reference: null }],
  credit: { reminder_on: null, terms: null, guarantor: null },
});

/** Une Sanya SY125-8 à 650 000 au comptant, sans châssis. */
export const ONE_SANYA = saleCommand({
  lines: [
    {
      article_id: "art-sy125-8",
      sale_mode: "unit",
      quantity: "1",
      unit_price: 650_000,
      details: [],
    },
  ],
  payments: [{ mode_id: "pm-cash", amount: 650_000, reference: null }],
});

/** Fiche d'une vente enregistrée avant l'ouverture, pour le rôle donné. */
export async function openSaleSheet(
  role: SaleRole,
  command: RecordSaleCommand = TWO_MOTOS,
  extra: Routes = {},
  exchange?: SaleServer["exchange"],
) {
  const view = renderSale(role, {
    path: `/s/${SHOP_A}/${role === "owner" ? "ventes" : "mes-ventes"}`,
    extra,
    ...(exchange === undefined ? {} : { exchange }),
  });
  const sale = await addSale(view.server, command);
  await view.router.navigate(`?id=${sale.id}`);
  await screen.findByRole("heading", { name: `Vente ${sale.number}` });
  return { ...view, sale };
}

/** Propriétaire : fiche puis « Retour ou échange ». */
export async function openReturn(command: RecordSaleCommand = TWO_MOTOS, extra: Routes = {}) {
  const view = await openSaleSheet("owner", command, extra);
  await view.user.click(await screen.findByRole("button", { name: "Retour ou échange" }));
  await screen.findByRole("heading", { name: /Retour ou échange/ });
  return view;
}
