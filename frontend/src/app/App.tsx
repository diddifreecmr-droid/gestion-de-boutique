import { useState } from "react";
import { createBrowserRouter, RouterProvider } from "react-router";
import { createServices, type AppServices } from "../core/services/createServices";
import { ServicesProvider } from "../core/services/ServicesProvider";
import { ToastProvider } from "../shared/ui";
import { appRoutes } from "./routes";

export interface AppProps {
  /** Injectable pour les tests ; par défaut, les services réels (fetch, localStorage). */
  services?: AppServices;
}

export function App({ services }: AppProps) {
  const [resolved] = useState(() => services ?? createServices());
  const [router] = useState(() => createBrowserRouter(appRoutes));
  return (
    <ServicesProvider services={resolved}>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </ServicesProvider>
  );
}
