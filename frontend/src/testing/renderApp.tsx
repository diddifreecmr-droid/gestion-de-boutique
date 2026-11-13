/** Rendu de l'application complète sur une adresse, avec un faux serveur (tests seulement). */
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { appRoutes } from "../app/routes";
import { createServices } from "../core/services/createServices";
import { ServicesProvider } from "../core/services/ServicesProvider";
import { ToastProvider } from "../shared/ui";
import { profileBody } from "./catalog";
import { createFakeFetch, json, SHOP_A, SHOP_B, type Reply } from "./fakeApi";
import { perActor } from "./servedProfile";

type Routes = Record<string, Reply | Reply[]>;

const PROFILE_PATH = /^GET \/api\/v1\/shops\/([^/]+)\/profile$/;

/**
 * Profil lu par la coquille de chaque boutique (modules actifs) : tous les modules, sauf si le
 * test fournit sa propre réponse (boutique minimale, module éteint…).
 */
function withShopProfiles(routes: Routes): Routes {
  const defaults = Object.fromEntries(
    [SHOP_A, SHOP_B].map((shopId) => [
      `GET /api/v1/shops/${shopId}/profile`,
      json(200, { ...profileBody("owner"), shop_id: shopId }),
    ]),
  );
  // Pas de copie : certains faux serveurs sont des `Proxy` qui servent toute route de la boutique.
  return new Proxy(routes, {
    get: (target, key): Reply | Reply[] | undefined => {
      const own: unknown = Reflect.get(target, key);
      const found = own !== undefined ? (own as Reply | Reply[]) : defaults[String(key)];
      const shopId = typeof key === "string" ? PROFILE_PATH.exec(key)?.[1] : undefined;
      if (found === undefined || shopId === undefined) return found;
      // Le vrai serveur sert le profil **par acteur** : menu et libellé du rôle de `GET /me`.
      const wrap = (reply: Reply) => perActor(target, shopId, reply);
      return Array.isArray(found) ? found.map(wrap) : wrap(found);
    },
  });
}

export function renderApp(path: string, routes: Routes) {
  const user = userEvent.setup();
  const fake = createFakeFetch(withShopProfiles(routes));
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
