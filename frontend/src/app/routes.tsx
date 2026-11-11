import { lazy, Suspense } from "react";
import type { RouteObject } from "react-router";
import { HomePage } from "./HomePage";
import { NotFoundPage } from "./NotFoundPage";

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
  { path: "/", element: <HomePage /> },
  ...devRoutes,
  { path: "*", element: <NotFoundPage /> },
];
