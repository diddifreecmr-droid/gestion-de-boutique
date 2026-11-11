/** Gestes communs des tests des Achats (tests seulement). */
import { screen, within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import type { Call } from "./fakeApi";

/** La ligne `n` (1-based) de la saisie : un groupe « Ligne n ». */
export function lineGroup(n: number): HTMLElement {
  return screen.getByRole("group", { name: `Ligne ${String(n)}` });
}

/** Cherche l'article dans la ligne `n` et le choisit parmi les propositions. */
export async function chooseArticle(user: UserEvent, text: string, name: string, n = 1) {
  const line = lineGroup(n);
  await user.type(within(line).getByLabelText("Article"), text);
  const list = await within(line).findByRole("list", { name: "Articles proposés" });
  await user.click(within(list).getByRole("button", { name }));
}

/** Remplit quantité et prix unitaire de la ligne `n`. */
export async function fillLine(user: UserEvent, quantity: string, price: string, n = 1) {
  const line = lineGroup(n);
  await user.type(within(line).getByLabelText("Quantité"), quantity);
  await user.type(within(line).getByLabelText(/^Prix unitaire/), price);
}

/** Corps de la `index`-ième requête `method` dont l'URL finit par `suffix`. */
export function sent(calls: readonly Call[], method: string, suffix: string, index = 0): unknown {
  const found = calls.filter((c) => c.method === method && c.url.endsWith(suffix));
  const call = found[index];
  if (call === undefined)
    throw new Error(`Aucune requête ${method} …${suffix} n° ${String(index)}`);
  return call.body;
}

/** Valeur d'une ligne du récapitulatif (« Coût unitaire final — Haojue HJ125-8 »). */
export function summaryValue(label: string): string {
  const summary = screen.getByRole("region", { name: "Récapitulatif" });
  const term = within(summary).getByText(label);
  const value = term.nextElementSibling;
  if (value === null) throw new Error(`Pas de valeur pour « ${label} »`);
  return value.textContent;
}
