/** Liste compacte du stock (une ligne dépliable par article) : la lire dans un test. */
import { screen, within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";

export const stockList = () => screen.findByRole("list", { name: "Stock par article" });

/** Ligne (`listitem`) de l'article dont le texte correspond à `name`. */
export async function stockItem(name: RegExp): Promise<HTMLElement> {
  const item = within(await stockList())
    .getAllByRole("listitem")
    .find((candidate) => name.test(candidate.textContent));
  if (item === undefined) throw new Error(`ligne ${name.source} absente`);
  return item;
}

/** Ligne de l'article, dépliée d'un appui : le détail (lieux, prix, coûts) apparaît dessous. */
export async function openStockItem(user: UserEvent, name: RegExp): Promise<HTMLElement> {
  const item = await stockItem(name);
  await user.click(within(item).getByRole("button", { name }));
  return item;
}
