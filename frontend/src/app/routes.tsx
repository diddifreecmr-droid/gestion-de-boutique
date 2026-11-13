import { lazy, Suspense } from "react";
import type { RouteObject } from "react-router";
import { ChangePinPage, CHANGE_PIN_PATH } from "../features/auth/ChangePinPage";
import {
  ADMIN_LOGIN_PATH,
  AdminLoginPage,
  LOGIN_PATH,
  LoginPage,
} from "../features/auth/LoginPage";
import { PublicOnly, RequireSession } from "./guards";
import { HomeRedirect } from "./HomeRedirect";
import { BareLayout } from "./layouts";
import { ModuleErrorPage } from "./ModuleErrorPage";
import { NotFoundPage } from "./NotFoundPage";
import { PLATFORM_PATH, SHOP_PICKER_PATH } from "./paths";
import { PlatformHome } from "./PlatformHome";
import { RoleHome } from "./RoleHome";
import { SectionPage } from "./SectionPage";
import { ShopPicker } from "./ShopPicker";
import { ShopShell } from "./ShopShell";

/** Chemin de la vitrine des composants (design-system.md § 9.2-5). */
export const UI_SHOWCASE_PATH = "/_ui";

/**
 * Vitrine `/_ui` : développement uniquement. Au build de production, `import.meta.env.DEV`
 * est remplacé par `false` : la branche et son import dynamique sont éliminés, aucun code
 * de la vitrine n'est émis dans `dist/` (vérifié par `npm run check:no-showcase`).
 */
const UiShowcase = import.meta.env.DEV ? lazy(() => import("./dev/UiShowcase")) : null;

const devRoutes: RouteObject[] =
  UiShowcase === null
    ? []
    : [
        {
          path: UI_SHOWCASE_PATH,
          element: (
            <Suspense fallback={null}>
              <UiShowcase />
            </Suspense>
          ),
        },
      ];

export const appRoutes: RouteObject[] = [
  {
    element: <PublicOnly />,
    children: [
      {
        element: <BareLayout />,
        children: [
          { path: LOGIN_PATH, element: <LoginPage /> },
          { path: ADMIN_LOGIN_PATH, element: <AdminLoginPage /> },
        ],
      },
    ],
  },
  {
    element: <RequireSession />,
    children: [
      {
        element: <BareLayout />,
        children: [
          { path: "/", element: <HomeRedirect /> },
          { path: CHANGE_PIN_PATH, element: <ChangePinPage /> },
          { path: SHOP_PICKER_PATH, element: <ShopPicker /> },
        ],
      },
      { path: PLATFORM_PATH, element: <PlatformHome /> },
      {
        path: "/s/:shopId",
        element: <ShopShell />,
        children: [
          // Un écran interrompu par 403 MODULE_DISABLED garde la coquille (specs § 15.1).
          { index: true, element: <RoleHome />, errorElement: <ModuleErrorPage /> },
          { path: ":section", element: <SectionPage />, errorElement: <ModuleErrorPage /> },
        ],
      },
    ],
  },
  ...devRoutes,
  { path: "*", element: <NotFoundPage /> },
];
