/** Rendu de l'application complète sur une adresse, avec un faux serveur (tests seulement). */
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { appRoutes } from "../app/routes";
import { createServices } from "../core/services/createServices";
import { ServicesProvider } from "../core/services/ServicesProvider";
import { ToastProvider } from "../shared/ui";
import { createFakeFetch, type Reply } from "./fakeApi";

export function renderApp(path: string, routes: Record<string, Reply | Reply[]>) {
  const user = userEvent.setup();
  const fake = createFakeFetch(routes);
  const services = createServices({ base: "/api", fetch: fake.fetch });
  const router = createMemoryRouter(appRoutes, { initialEntries: [path] });
  const view = render(
    <ServicesProvider services={services}>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </ServicesProvider>,
  );
  return { ...view, router, services, fake, user };
}
